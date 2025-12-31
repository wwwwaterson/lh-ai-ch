import os


class Settings:
    def __init__(self):
        # Sensitive configuration - must be provided via environment variables
        self.DATABASE_URL: str = os.getenv("DATABASE_URL")
        self.SECRET_KEY: str = os.getenv("SECRET_KEY")
        
        # Non-sensitive configuration - can have defaults
        self.UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/tmp/docproc_uploads")
        
        # Validate required environment variables
        self._validate_required_config()
    
    def _validate_required_config(self):
        """Fail fast if required environment variables are missing"""
        missing = []
        
        if not self.DATABASE_URL:
            missing.append("DATABASE_URL")
        if not self.SECRET_KEY:
            missing.append("SECRET_KEY")
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Please set them before starting the application."
            )


settings = Settings()
