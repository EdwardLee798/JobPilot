"""
投递记录实时监控服务
监控Func2数据库的变化，自动同步到状态跟踪模块
"""
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
FUNC2_DB = PROJECT_ROOT / "Func2_AutoApplication" / "db" / "getjobs.db"
TRACKING_DB = Path(__file__).parent.parent.parent / "data" / "database" / "tracking.db"


class DeliveryMonitor:
    """投递记录监控器"""

    def __init__(self, check_interval=5):
        """
        初始化监控器

        Args:
            check_interval: 检查间隔（秒），默认5秒
        """
        self.check_interval = check_interval
        self.is_running = False
        self.monitor_thread = None
        self.last_check_time = None
        self.stats = {
            'total_synced': 0,
            'last_sync_time': None,
            'last_sync_count': 0
        }

    def start(self):
        """启动监控服务"""
        if self.is_running:
            logger.warning("监控服务已在运行中")
            return

        self.is_running = True
        self.last_check_time = datetime.now()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"投递监控服务已启动，检查间隔: {self.check_interval}秒")

    def stop(self):
        """停止监控服务"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("投递监控服务已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                self._check_and_sync()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(self.check_interval)

    def _check_and_sync(self):
        """检查并同步新记录"""
        try:
            # 检查Func2数据库是否存在
            if not FUNC2_DB.exists():
                return

            # 获取新的投递记录
            new_records = self._get_new_records()

            if new_records:
                # 同步到tracking数据库
                synced_count = self._sync_records(new_records)

                if synced_count > 0:
                    self.stats['total_synced'] += synced_count
                    self.stats['last_sync_time'] = datetime.now()
                    self.stats['last_sync_count'] = synced_count
                    logger.info(f"✓ 自动同步 {synced_count} 条新记录")

        except Exception as e:
            logger.error(f"检查同步出错: {e}")

    def _get_new_records(self):
        """获取新的投递记录"""
        try:
            conn = sqlite3.connect(str(FUNC2_DB))
            cursor = conn.cursor()

            # 获取上次检查时间之后的新记录
            if self.last_check_time:
                time_str = self.last_check_time.strftime('%Y-%m-%d %H:%M:%S')

                # 查询新的已投递记录
                cursor.execute("""
                    SELECT job_name, company_name, job_description, delivery_status, created_at, updated_at
                    FROM boss_data
                    WHERE delivery_status = '已投递'
                    AND (updated_at > ? OR created_at > ?)
                    ORDER BY updated_at DESC
                """, (time_str, time_str))
            else:
                # 首次运行，获取所有已投递记录
                cursor.execute("""
                    SELECT job_name, company_name, job_description, delivery_status, created_at, updated_at
                    FROM boss_data
                    WHERE delivery_status = '已投递'
                    ORDER BY updated_at DESC
                """)

            rows = cursor.fetchall()
            conn.close()

            # 更新检查时间
            self.last_check_time = datetime.now()

            records = []
            for row in rows:
                records.append({
                    'job_name': row[0] or '',
                    'company_name': row[1] or '',
                    'job_description': row[2] or '',
                    'delivery_status': row[3] or '',
                    'created_at': row[4] or '',
                    'updated_at': row[5] or ''
                })

            return records

        except Exception as e:
            logger.error(f"获取新记录失败: {e}")
            return []

    def _sync_records(self, records):
        """同步记录到tracking数据库"""
        try:
            # 确保tracking数据库目录存在
            TRACKING_DB.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(str(TRACKING_DB))
            cursor = conn.cursor()

            synced_count = 0

            for record in records:
                job_title = record.get('job_name', '').strip()
                company_name = record.get('company_name', '').strip()
                job_description = record.get('job_description', '').strip()
                created_at = record.get('created_at', '')

                if not job_title or not company_name:
                    continue

                # 检查是否已存在
                cursor.execute('''
                    SELECT job_id FROM job_summary
                    WHERE job_title = ? AND company_name = ?
                ''', (job_title, company_name))

                existing = cursor.fetchone()
                if existing:
                    continue

                # 插入job_summary
                cursor.execute('''
                    INSERT INTO job_summary (job_title, company_name, job_desc, tracking_method)
                    VALUES (?, ?, ?, ?)
                ''', (job_title, company_name, job_description, 'Boss直聘自动投递'))

                job_id = cursor.lastrowid

                # 解析时间戳
                event_time = self._parse_timestamp(created_at)

                # 插入状态：已申请
                cursor.execute('''
                    INSERT INTO application_status (job_id, status_update, event_time)
                    VALUES (?, ?, ?)
                ''', (job_id, '已申请', event_time))

                synced_count += 1
                logger.info(f"  → {company_name} - {job_title}")

            conn.commit()
            conn.close()

            return synced_count

        except Exception as e:
            logger.error(f"同步记录失败: {e}")
            return 0

    def _parse_timestamp(self, created_at):
        """解析时间戳"""
        try:
            if created_at:
                if isinstance(created_at, str):
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            dt = datetime.strptime(created_at, fmt)
                            return dt.timestamp()
                        except:
                            continue
                else:
                    return float(created_at) if created_at else time.time()
            return time.time()
        except:
            return time.time()

    def get_stats(self):
        """获取监控统计信息"""
        return {
            'is_running': self.is_running,
            'check_interval': self.check_interval,
            'total_synced': self.stats['total_synced'],
            'last_sync_time': self.stats['last_sync_time'].isoformat() if self.stats['last_sync_time'] else None,
            'last_sync_count': self.stats['last_sync_count'],
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None
        }


# 全局监控器实例
_monitor = None


def get_monitor():
    """获取监控器实例"""
    global _monitor
    if _monitor is None:
        _monitor = DeliveryMonitor(check_interval=5)
    return _monitor


def start_monitor():
    """启动监控服务"""
    monitor = get_monitor()
    monitor.start()
    return monitor


def stop_monitor():
    """停止监控服务"""
    monitor = get_monitor()
    monitor.stop()


def get_monitor_stats():
    """获取监控统计"""
    monitor = get_monitor()
    return monitor.get_stats()
