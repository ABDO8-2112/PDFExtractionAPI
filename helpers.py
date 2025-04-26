import mysql.connector
import json
from typing import Dict, Any

def save_json_to_mysql(data: Dict[str, Any], host: str, user: str, password: str, database: str) -> None:
    """Save extracted JSON into MySQL database (for table pdfextractiondata)."""
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=3306
        )

        if connection.is_connected():
            cursor = connection.cursor()

           
            pdf_file_name = data["response"]["book"] + ".pdf" 
            json_content = json.dumps(data["response"])        

            # Insert query
            insert_query = """
                INSERT INTO pdfextractiondata (PDFFileName, JSONContent, CreatedAt)
                VALUES (%s, %s, NOW())
            """
            values = (pdf_file_name, json_content)

            cursor.execute(insert_query, values)
            connection.commit()

            print("✅ Data inserted successfully into pdfextractiondata.")
        else:
            print("❌ Failed to connect to the MySQL database.")

    except mysql.connector.Error as error:
        print(f"❌ MySQL error: {error}")

    except Exception as e:
        print(f"❌ General error: {e}")

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
            print("🔒 MySQL connection closed.")
