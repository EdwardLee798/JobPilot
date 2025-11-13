# Project Structure

```
combine/
├── README.md                   # Complete documentation
├── GETTING_STARTED.md          # Quick start guide
├── PROJECT_STRUCTURE.md        # This file
├── LICENSE                     # License file
│
├── resume.json                 # Your resume data (EDIT THIS)
├── .env                        # AI API configuration (OPTIONAL)
│
├── auto_start.sh              # 🚀 Main automated startup script
├── stop.sh                    # 🛑 Stop all services
├── quick_setup.sh             # ⚙️  Initial configuration wizard
├── config_from_json.py        # 🔧 Configure from resume.json
├── update_config.sh           # 🔧 Manual configuration helper
├── check_setup.sh             # ✅ Verify system requirements
│
├── build.gradle.kts           # Gradle build configuration
├── settings.gradle            # Gradle settings
├── gradlew                    # Gradle wrapper (Unix)
├── gradlew.bat                # Gradle wrapper (Windows)
├── gradle/                    # Gradle wrapper files
│   └── wrapper/
│
├── src/                       # Java source code
│   └── main/
│       ├── java/              # Application code
│       │   └── com/getjobs/
│       │       ├── GetJobsApplication.java      # Main entry point
│       │       ├── application/                 # Application layer
│       │       │   ├── config/                 # Spring Boot config
│       │       │   ├── controller/             # REST API controllers
│       │       │   ├── entity/                 # Database entities
│       │       │   ├── service/                # Business logic
│       │       │   └── init/                   # Initialization
│       │       └── worker/                     # Worker layer
│       │           ├── boss/                   # Boss Zhipin logic
│       │           ├── liepin/                 # Liepin logic
│       │           ├── manager/                # Browser automation
│       │           ├── service/                # Job delivery services
│       │           └── dto/                    # Data transfer objects
│       └── resources/
│           ├── application.yaml                # Application config
│           ├── banner.txt                      # Startup banner
│           └── images/                         # Resources
│
├── db/                        # SQLite database
│   └── getjobs.db            # Application database
│       ├── boss_config       # Boss search configuration
│       ├── liepin_config     # Liepin configuration
│       ├── boss_job_data     # Boss application records
│       ├── liepin_data       # Liepin application records
│       ├── cookie            # Login cookies
│       └── blacklist         # Company blacklist
│
├── logs/                      # Application logs
│   └── app.log               # Main log file
│
├── build/                     # Build output (auto-generated)
│   ├── classes/
│   ├── libs/
│   └── ...
│
├── front/                     # Frontend (not used in CLI mode)
│   └── ...
│
├── doc/                       # Documentation
│   └── imgs/
│
└── target/                    # Additional build artifacts
    └── logs/
