import logging
import os
import threading
from dotenv import load_dotenv
import pyodbc

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='logs/bot.log',
    filemode='a',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        load_dotenv("ini.env", override=True)
        self.__driver=os.getenv("DRIVER")
        self.__server=os.getenv("SERVER")
        self.__db=os.getenv("DATABASE")
        self.__user_name=os.getenv("USERNAME")
        self.__password=os.getenv("PASSWORD")
        self._lock = threading.Lock()
        self._conn = None
        self._connect()


    def _connect(self):
        try:
            conn_str = (
                f"DRIVER={self.__driver};"
                f"SERVER={self.__server};"
                f"DATABASE={self.__db};"
                f"UID={self.__user_name};"
                f"PWD={self.__password};"
                f"Encrypt=yes;"
                f"TrustServerCertificate=yes"
            )
            self._conn = pyodbc.connect(conn_str, autocommit=False)
            logger.info("Database connection was create successfully.")
        except Exception as e:
            logger.error(f"Error connection to database: {e}")
        

    def execute_query(self, sql_query, params=None):
        with self._lock:
            try:
                cursor = self._conn.cursor()
                if params:
                    cursor.execute(sql_query, params)
                else:
                    cursor.execute(sql_query)
                
                res = cursor.fetchall()
                return res
            except Exception as e:
                logger.error(f"Error executing request: {e}")
                return []
            finally:
                cursor.close()


    def execute_edit_query(self, sql_query, params=None):
        with self._lock:
            try:
                cursor = self._conn.cursor()
                if params:
                    cursor.execute(sql_query, params)
                else:
                    cursor.execute(sql_query)
                return True
            except Exception as e:
                logger.error(f"Error executing change: {e}")
                return False
            finally:
                cursor.close()
    

    def execute_procedure(self, proc_name, *params):
        placeholders = ", ".join(["?"] * len(params))
        sql = f"{{CALL dbo.{proc_name} ({placeholders})}}"
        
        
        with self._lock:
            try:
                cursor = self._conn.cursor()

                cursor.execute(sql, params)
                self._conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error executing procedure: {e}")
                return False
            finally:
                cursor.close()
    

    def query_procedure(self, proc_name, *params):
        placeholders = ", ".join(["?"] * len(params))
        sql = f"{{CALL dbo.{proc_name} ({placeholders})}}"
        
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(sql, params)
                res = cursor.fetchall()
                return res
            except Exception as e:
                logger.error(f"Error executing procedure: {e}")
                return None
            finally:
                cursor.close()


    def close(self):
        if self._conn:
            self._conn.close()