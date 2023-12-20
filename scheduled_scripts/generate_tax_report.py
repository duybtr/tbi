import base64
import gspread
import psycopg2
import pandas as pd
from datetime import datetime
import time
import locale
import os
from google.cloud import secretmanager
locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )

def format_text_req(sheet, startRowIndex, endRowIndex, startColumnIndex, endColumnIndex, text_color, font_size, is_bold, background_color):
    text_formatting =  {
      "repeatCell": {
        "range": {
          "sheetId": sheet.id,
          "startRowIndex": startRowIndex,
          "endRowIndex": endRowIndex,
          "startColumnIndex": startColumnIndex,
          "endColumnIndex": endColumnIndex,
        },
        "cell": {
          "userEnteredFormat": {
            "backgroundColor": background_color,
            "horizontalAlignment" : "CENTER",
            "textFormat": {
              "foregroundColor": text_color,
              "fontSize": font_size,
              "bold": is_bold
            }
          }
        },
        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
      }
    }
    return text_formatting

def format_border_req(sheet, startRow, endRow, startCol, endCol):
    color = {
      "red": 0,
      "green": 0,
      "blue": 0,
      "alpha": 1
    }
    border_style = {
        "style": "SOLID",
        "width": 1,
        "color": color
    }
    border_req = {
        "updateBorders": {
            "range": {
              "sheetId": sheet.id,
              "startRowIndex": startRow,
              "endRowIndex": endRow,
              "startColumnIndex": startCol,
              "endColumnIndex": endCol
            },
            "top": border_style,
             "bottom": border_style,
            "left": border_style,
            "right": border_style,
            "innerHorizontal": border_style,
            "innerVertical": border_style
        }
    }
    return border_req

def update_dimensions(sheet, startIndex, endIndex, size):
    request = {
      "updateDimensionProperties": {
        "range": {
          "sheetId": sheet.id,
          "dimension": "COLUMNS",
          "startIndex": startIndex,
          "endIndex": endIndex
        },
        "properties": {
          "pixelSize": 160
        },
        "fields": "pixelSize"
      }
    }
    return request

def merge_cells(sheet, startRowIndex, endRowIndex, startColumnIndex, endColumnIndex):
    merge_cells = {
     "mergeCells": {
        "range": {
          "sheetId": sheet.id,
          "startRowIndex": startRowIndex,
          "endRowIndex": endRowIndex,
          "startColumnIndex": startColumnIndex,
          "endColumnIndex": endColumnIndex
        },
        "mergeType": "MERGE_ROWS"
      }
    }
    return merge_cells

def access_secret_version(secret_version_id):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    response = client.access_secret_version(name=secret_version_id)

    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')

def gen_tax_report(request):
    gc = gspread.service_account(filename='tbi-finance-a3f1a4fd0be6.json')
    year = datetime.now().year
    if request.args and request.args.get('previous') == 'Y':
      year = year - 1
     
    report_name = 'Tran Ba Investment Group Tax Report ' + str(year)
    print('********* Report {} was requested ********'.format(report_name))
    sh = None
    try:
        sh = gc.open(report_name)
    except:
        sh = gc.create(report_name)
        sh.share('duytran2310@gmail.com', perm_type='user', role='writer')
        sh.share('huybtran86@gmail.com', perm_type='user', role='writer')
        sh.share('mle43678@gmail.com', perm_type='user', role='writer')

    
    worksheets = sh.worksheets()
    reqs = [{"addSheet": {"properties": {"index": 0}}}] + [{"deleteSheet": {"sheetId": s.id}} for s in worksheets]
    sh.batch_update({"requests": reqs})
    blank_sheet = sh.get_worksheet(0)

    env = os.environ.get('env')
    if env == 'PROD':
      db_host = "/cloudsql/tbi-finance:us-central1:tbi-postgres"
    else:
      db_host = "localhost"
    
    db_username = access_secret_version("projects/334572487877/secrets/db_username/versions/1")
    db_password = access_secret_version("projects/334572487877/secrets/db_password/versions/2")
  
    conn = psycopg2.connect(host=db_host, port = 5432, database="postgres", user=db_username, password=db_password)
    
    # Create a cursor object
    cur = conn.cursor()
    properties = pd.read_sql_query("SELECT * FROM tbi_properties", conn)
    df = pd.read_sql_query("SELECT * FROM tbi_tax_report WHERE DATE_PART('year', record_date) = {}".format(year), conn)
    df['record_date'] = df['record_date'].astype(str)
    df['date_filed'] = df['date_filed'].astype(str)

    n = 5
    properties_sorted = sorted(set(properties.address), reverse=True)
    properties_sorted = ['Summary'] + properties_sorted
    for properties_subset in [properties_sorted[i:i + n] for i in range(0, len(properties_sorted), n)]:
        for p in properties_subset:
          print(p)
          worksheet = sh.add_worksheet(title=p, rows=100, cols=20)
          if p == 'Summary':
              df_address = df
          else:
              df_address = df[(df.address == p)]
          df_expense =  df_address[df_address.accounting_classification == 'Expense'].groupby(['category']).sum().reset_index()
          df_expense.category = df_expense.category.str.replace('_', ' ')
          df_expense.category = df_expense.category.str.title()
          df_expense.amount = df_expense.amount.apply(locale.currency, grouping=True)
          total_revenue = df_address[df_address.accounting_classification == 'Revenue'].amount.sum()
          total_expense = df_address[df_address.accounting_classification == 'Expense'].amount.sum()
          net_income = df_address.amount.sum()
          total_revenue = locale.currency(total_revenue, grouping = True)
          total_expense = locale.currency(total_expense, grouping = True)
          net_income = locale.currency(net_income, grouping = True)

          header_cells = worksheet.range('A1:B1')
          summary_cells = worksheet.range('A2:B4')
          value_list = ['Total Revenue', total_revenue, 'Total Expense', total_expense, 'Net Income', net_income]

          header_cells[0].value = p
          for i,cell in enumerate(summary_cells):
              cell.value = value_list[i]

          worksheet.update_cells(header_cells + summary_cells)

          worksheet.update('A6', [[c.capitalize() for c in df_expense.columns.values.tolist()]] + df_expense.values.tolist())

          top_start_row = 1
          top_end_row = top_start_row + 3
          top_start_col = 0
          top_end_col = top_start_col + 2
          bottom_start_row = top_end_row + 1
          bottom_end_row = bottom_start_row + len(df_expense) + 1
          bottom_start_col = 0
          bottom_end_col = len(df_expense.columns)
          text_color = {
            "red": 0.0,
            "green": 0.0,
            "blue": 0.0
          }
          background_color =  {
            "red": 1.0,
            "green": 1.0,
            "blue": 1.0
          }
          formatting_request = []
          formatting_request.append(format_border_req(worksheet, top_start_row, top_end_row, top_start_col, top_end_col))
          formatting_request.append(format_border_req(worksheet, bottom_start_row, bottom_end_row, bottom_start_col, bottom_end_col))
          formatting_request.append(merge_cells(worksheet, 0, 1, 0, 2))
          formatting_request.append(format_text_req(worksheet, 5, 6, 0, 2, text_color, 11, True, background_color))
          formatting_request.append(format_text_req(worksheet, 0, 1, 0, 2, text_color, 12, True, background_color))
          formatting_request.append(update_dimensions(worksheet, 0, 1, 160))
          sh.batch_update({"requests":formatting_request})
        time.sleep(60)
    sh.del_worksheet(blank_sheet)
    return "Success"

