# 初步技术路线总结
## 1. 简历识别
### 1.1 整体流程
用户上传文件 → 后端保存临时文件 → 文件类型判断 → 文字提取（OCR/PDF解析） → 简历结构化解析（NLP/API） → 存储至数据库 → 提供API/后台管理

### 1.2 技术实现细节
1. **前端实现**
   - 框架：React（也可选Vue/Angular）
   - 核心功能：提供文件上传控件，支持图片和PDF格式。上传后调用后端API传送文件。

2. **后端文件接收**
   - 核心功能：接收到文件后保存至本地或云存储。判断文件类型（图片或PDF）。

3. **文件内容提取**
   - 图片处理：调用OCR工具（Tesseract、百度OCR API）识别图片中的文字。
   - PDF处理：优先解析PDF文本（pdfminer、PyPDF2），若为扫描件则先转图片再OCR。
   - 注意事项：需注意中文简历OCR准确率，云服务API效果一般优于开源Tesseract。

4. **文本结构化分析**
   - 核心目标：对获得的文本进行结构化分析，抽取关键信息（姓名、电话、邮箱、教育、工作经历等）。
   - 处理方式：
     - 简单用正则表达式提取邮箱、电话。
     - 用NLP模型（如BERT、spaCy）对文本分块、实体识别。
     - 或集成成熟的简历解析API/服务。

5. **数据存储**
   - 核心功能：将结构化数据存入数据库（如MongoDB或MySQL）。
   - 附加功能：可以存储原文件路径，供后续下载/查看。

6. **接口与后台管理**
   - 接口功能：提供API接口查询简历档案。
   - 后台功能：后台管理页面查看/编辑简历。


## 2. 网站自动化填写
### 2.1 整体流程
用户输入岗位申请网址 → 后端自动化脚本打开并识别表单 → 后台智能匹配简历档案信息 → 自动填充并推进到提交前 → 前端同步自动化界面供用户审核 → 用户确认 → 完成提交

### 2.2 技术实现细节
1. **前端实现**
   - 关联说明：同1.1中的前端技术框架基础
   - 核心功能：
     - 提供网址输入界面，显示自动化浏览器实时界面（截图/直播/远程控制）。
     - 提供用户“确认无误”与“最终提交”按钮。
     - 提供URL输入框，提交后通过API发送到后端。

2. **后端实现**
   - 推荐框架：FastAPI（Python）
   - 核心功能：
     - 接收前端传递的岗位URL。
     - 启动自动化浏览器。
     - 解析页面表单。
     - 字段语义识别与匹配。
     - 自动填充与流程控制。
     - 与前端通信，推送实时画面。
     - 响应“最终提交”请求。
   - 代码示例：
     ```python
     from playwright.sync_api import sync_playwright
     def open_page_and_find_forms(url):
         with sync_playwright() as p:
             browser = p.chromium.launch(headless=True)
             page = browser.new_page()
             page.goto(url, timeout=60000)
             forms = page.query_selector_all('form')
             # 截图或录屏用于前端展示
             page.screenshot(path='form_page.png')
             # ...后续表单分析
             browser.close()
     ```

3. **浏览器自动化填写**
   - 关联说明：同（2）中推荐的Playwright框架
   - 核心功能：
     - 无头模式打开岗位页面。
     - 识别所有表单（form）元素。
     - 解析input、select、textarea等控件。
     - 截图/直播/远程同步画面。
     - 自动化表单填写、按钮点击。
   - 代码示例：
     ```python
     for form in forms:
         fields = []
         for el in form.query_selector_all('input, select, textarea'):
             field = {
                 "name": el.get_attribute('name'),
                 "id": el.get_attribute('id'),
                 "type": el.get_attribute('type'),
                 "placeholder": el.get_attribute('placeholder'),
                 "label": get_label_text(el)
             }
             fields.append(field)
     ```

4. **字段语义识别**
   - 基础方案：可以定义字典匹配
   - 代码示例：
     ```python
     FIELD_MAP = {
         "name": ["姓名", "name", "full name"],
         "phone": ["手机号", "手机", "电话", "mobile", "cellphone"],
         "email": ["邮箱", "email", "e-mail"],
         # ...
     }
     ```
   - 改进方案：NLP实体识别+语义匹配（spaCy、transformers/BERT、LLM或API如百度NLP）
   - 改进作用：解决“手机号、mobile、电话、cell phone”同义问题，实现字段智能对齐


## 3. 岗位分析与简历优化
### 3.1 整体流程
用户输入JD（文本或链接）（也可以根据第二部分读取的链接来）→ JD内容获取与解析（爬取/HTML解析/OCR）→ JD关键信息抽取（NLP/LLM/规则）→ 简历档案检索与对比（结构化简历/RAG）→ 差距分析与建议生成（LLM+RAG）→ 优化版简历生成（LLM+RAG）→ 前端展示建议和优化简历，用户可编辑/下载 → 对接自动投递流程

### 3.2 具体实现流程
1. **JD关键信息抽取**
   - 技术手段：
     - 规则+正则提取（如“任职要求”、“技能要求”标题下内容）。
     - NLP实体识别（如spaCy、transformers NER，抽取技能、学历、经验年限、语言要求等）。
     - 领域词表/知识库（如技能、职位类别、学历标准的词典）。
     - LLM大模型抽取：调用GPT-4、Qwen、通义千问，prompt如“请提取该JD的核心要求、必备技能、优先条件”。
   - JD信息抽取Prompt示例：“请从以下职位描述中提取：职位名称、要求技能、学历要求、经验年限、语言要求、优先条件。”
   - 输出结构举例：
     ```json
     { 
         "position": "后端开发工程师", 
         "skills": ["Python", "Django", "MySQL", "Docker"], 
         "education": "本科及以上", 
         "experience": "3年以上后端开发经验", 
         "language": "英语读写", 
         "plus": ["有分布式系统经验优先"] 
     }
     ```

2. **用户简历档案检索**
   - 数据基础：前文已存储结构化简历档案（MongoDB等）。
   - 检索逻辑：检索与JD要求相关字段，如skills、education、experience等。
   - 进阶方案：可用向量检索（如FAISS、Milvus），将JD抽取内容与简历内容做embedding后检索（RAG部分）。

3. **差距分析与优化建议生成**
   - 差距分析：
     - 逐项对比JD要求与用户简历内容。
     - 检查缺失项（如JD要求“Python”，简历未体现则提示补充）。
     - 检查亮点项（如JD优先项用户已具备，则建议突出）。
   - 建议生成：
     - 规则引擎：针对缺失或亮点自动生成建议文本。
     - 利用LLM与RAG（Retrieval-Augmented Generation）：结合JD和简历内容生成个性化建议，例如prompt：“请帮我生成简历优化建议，突出JD要求与我的匹配点，并补充不足。”
   - RAG流程：
     - 将JD和简历内容embedding到知识库。
     - 检索简历写作模板、行业最佳实践、JD相关表达等内容。
     - 作为context输入LLM，生成更贴合JD的优化简历。