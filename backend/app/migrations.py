import os
import asyncio
import logging
from app.config import settings
from tortoise import Tortoise
import asyncpg

logger = logging.getLogger(__name__)

async def run_migrations():
    """Run database migrations for schema updates"""
    try:
        # First, ensure Tortoise has created all tables
        await Tortoise.init(
            db_url=settings.DATABASE_URL,
            modules={"models": ["app.models"]}
        )
        
        # Generate schemas first to ensure tables exist
        await Tortoise.generate_schemas()
        
        # Now connect with asyncpg to run manual migrations if needed
        conn = Tortoise.get_connection("default")
        
        # Check if users table exists and has necessary columns
        try:
            # Check if the last_summary_count column exists
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='last_summary_count'
            """
            result = await conn.execute_query(query)
            
            if not result[1]:  # Column doesn't exist
                logger.info("Adding 'last_summary_count' column to users table...")
                await conn.execute_query(
                    "ALTER TABLE users ADD COLUMN last_summary_count INTEGER DEFAULT 0"
                )
                logger.info("Migration for last_summary_count completed successfully")
            
            # Check if the entry_count column exists
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='entry_count'
            """
            result = await conn.execute_query(query)
            
            if not result[1]:  # Column doesn't exist
                logger.info("Adding 'entry_count' column to users table...")
                await conn.execute_query(
                    "ALTER TABLE users ADD COLUMN entry_count INTEGER DEFAULT 0"
                )
                logger.info("Migration for entry_count completed successfully")
            
            # Check if the emotion_tags column exists in journal_entries
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='journal_entries' AND column_name='emotion_tags'
            """
            result = await conn.execute_query(query)
            
            if not result[1]:  # Column doesn't exist
                logger.info("Adding 'emotion_tags' column to journal_entries table...")
                await conn.execute_query(
                    "ALTER TABLE journal_entries ADD COLUMN emotion_tags JSONB DEFAULT '[]'::jsonb"
                )
                logger.info("Migration for emotion_tags completed successfully")
                
            # Check if the title column exists in journal_entries
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='journal_entries' AND column_name='title'
            """
            result = await conn.execute_query(query)
            
            if not result[1]:  # Column doesn't exist
                logger.info("Adding 'title' column to journal_entries table...")
                await conn.execute_query(
                    "ALTER TABLE journal_entries ADD COLUMN title VARCHAR(100) NULL"
                )
                logger.info("Migration for title completed successfully")
                
            # Check if the image_url column exists in journal_entries
            query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='journal_entries' AND column_name='image_url'
            """
            result = await conn.execute_query(query)
            
            if not result[1]:  # Column doesn't exist
                logger.info("Adding 'image_url' column to journal_entries table...")
                await conn.execute_query(
                    "ALTER TABLE journal_entries ADD COLUMN image_url VARCHAR(500) NULL"
                )
                logger.info("Migration for image_url completed successfully")
                
        except Exception as e:
            # This could happen if the tables don't exist yet
            # but that's okay because Tortoise.generate_schemas() will create it
            logger.warning(f"Migration check error: {str(e)}")
            # Just continue, as the table will be created with all columns by Tortoise
        
        return True
    except Exception as e:
        logger.error(f"Migration error: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(run_migrations())
