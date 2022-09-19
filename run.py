import boto3
import io
import pandas as pd
import numpy as np
import os
import requests
import json
import urllib
import xlsxwriter

from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File
from office365.runtime.auth.client_credential import ClientCredential

from datetime import datetime

q = boto3.client('sqs', region_name="us-west-1")
q_url = 'https://sqs.us-west-1.amazonaws.com/486878523588/InvoiceFiles'


#########################################################
def get_secret(secret_name, region_name):

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    get_secret_value_response = client.get_secret_value(SecretId=secret_name)

    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
    else:
        secret = base64.b64decode(get_secret_value_response['SecretBinary'])

    return json.loads(secret)[secret_name]


#########################################################
class sharepoint:
    def __init__(self):
        self.app_principal = {
            'client_id': '4a5f1c0c-977a-442b-9526-c9a134172e79',
            'client_secret': get_secret("sharepointfilesharesvc_pacesupply_com_client_secret", "us-west-1"),
            'baseurl': 'https://pacesupplyinc-my.sharepoint.com/personal/sharepointfilesharesvc_pacesupply_com'
        }

    def get_files(self, path):
        libraryRoot = self.get_creds().web.get_folder_by_server_relative_url(path)
        libraryRoot.expand(["Files", "Folders"]).get().execute_query()

        return libraryRoot.files

    def get_file(self, path):
        response = File.open_binary(self.get_creds(), path)

        return response

    def get_file_as_dataframe(self, path, converters={}):
        response = self.get_file(path)

        bytes_file_obj = io.BytesIO()
        bytes_file_obj.write(response.content)
        bytes_file_obj.seek(0)  # set file object to start
        return pd.read_excel(bytes_file_obj, converters=converters)

    def put_dataframe_to_file(self, df, path, filename):
        try:
            bytes_file_obj = io.BytesIO()
            df.to_excel(bytes_file_obj, index=False)
            bytes_file_obj.seek(0)

            sp_folder = self.get_creds().web.get_folder_by_server_relative_url(path)
            sp_folder.upload_file(filename, bytes_file_obj).execute_query()
        except:
            print("Error uploadig file {}".format(filename))

    def put_dataframe_to_file_formated(self, df, path, filename):
        try:

            bytes_file_obj = io.BytesIO()
            # df.to_excel(bytes_file_obj, index=False)
            writer = pd.ExcelWriter(bytes_file_obj, engine='xlsxwriter')

            df.to_excel(writer, sheet_name='Sheet1', index=False)

            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            format = workbook.add_format({'text_wrap': True,
                                          'bold': True,
                                          'valign': 'top',
                                          'align': 'center',
                                          'bg_color': '#E5FFE5',
                                          'bottom': 1,
                                          'right': 1,
                                          'border_color': '#666666'})

            # worksheet.set_row(0, None, format)

            worksheet.set_row(0, 35, format)

            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, format)

            for column in df:
                column_length = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column)
                writer.sheets['Sheet1'].set_column(col_idx, col_idx, column_length+2)

            worksheet.freeze_panes(1, 0)
            writer.save()

            bytes_file_obj.seek(0)

            sp_folder = self.get_creds().web.get_folder_by_server_relative_url(path)
            sp_folder.upload_file(filename, bytes_file_obj).execute_query()
        except:
            print("Error uploadig file {}".format(filename))

    def get_creds(self):
        if hasattr(self, "ctx"):
            return self.ctx

        credentials = ClientCredential(self.app_principal['client_id'], self.app_principal['client_secret'])
        self.ctx = ClientContext(self.app_principal['baseurl']).with_credentials(credentials)
        return self.ctx


#########################################################
class misapi:
    def __init__(self, customer=None):
        if customer:
            self.customer = customer
        # self.baseurl = "http://pace-mis:9191/"
        self.baseurl = "http://mis-api-b.pacesupply.com:9191/"

    def getvoucher(self, invoiceno, vendno, retryct=0):
        baseurl = self.baseurl
        endpoint = "pacehj/API.GET.VOUCHER.DETAIL/json/?invoiceno=" + str(invoiceno) + "&vendno=" + str(vendno)
        newbaseurl = "https://qlbimadsonxr7dcdf2nsd2cxbm0nzsll.lambda-url.us-west-1.on.aws/?url="
        # endpoint = "ws/rest/price"

        newbaseurl = newbaseurl + urllib.parse.quote(baseurl + endpoint, safe='')
        # print(newbaseurl)

        headers = {"X-API-KEY": "None"}
        # response = requests.get(baseurl + endpoint, headers=headers)
        response = requests.get(newbaseurl, headers=headers, timeout=60)
        try:
            rjson = response.json()
        except:
            print("error retrying {}".format(retryct))
            if (retryct < 3):
                return self.getvoucher(invoiceno, vendno, retryct+1)
        return rjson['vouchers']

    def getreceivedpos(self, vendno, retryct=0):
        baseurl = self.baseurl
        endpoint = "pacehj/API.GET.RECEIVEDPOS.BYVENDOR/json/?vendno=" + str(vendno)
        newbaseurl = "https://qlbimadsonxr7dcdf2nsd2cxbm0nzsll.lambda-url.us-west-1.on.aws/?url="
        # endpoint = "ws/rest/price"

        newbaseurl = newbaseurl + urllib.parse.quote(baseurl + endpoint, safe='')
        # print(newbaseurl)

        headers = {"X-API-KEY": "None"}
        # response = requests.get(baseurl + endpoint, headers=headers)
        response = requests.get(newbaseurl, headers=headers, timeout=60)
        # rjson = response.json()
        try:
            rjson = response.json()
        except:
            print("error retrying {}".format(retryct))
            if (retryct < 3):
                return self.getreceivedpos(vendno, retryct+1)
        return rjson['purchaseorders']

    def getvouchers_nocheck(self, vendno, retryct=0):
        baseurl = self.baseurl
        endpoint = "pacehj/API.GET.VOUCHER.NOCHECK/json/?vendno=" + str(vendno)
        newbaseurl = "https://qlbimadsonxr7dcdf2nsd2cxbm0nzsll.lambda-url.us-west-1.on.aws/?url="
        # endpoint = "ws/rest/price"

        newbaseurl = newbaseurl + urllib.parse.quote(baseurl + endpoint, safe='')
        # print(newbaseurl)

        headers = {"X-API-KEY": "None"}
        # response = requests.get(baseurl + endpoint, headers=headers)
        response = requests.get(newbaseurl, headers=headers, timeout=60)
        # rjson = response.json()
        try:
            rjson = response.json()
        except:
            print("error retrying {}".format(retryct))
            if (retryct < 3):
                return self.getvouchers_nocheck(vendno, retryct+1)
        return rjson['vouchers']


#########################################################
def getmessage():

    response = q.receive_message(
        QueueUrl=q_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )

    if "Messages" in response:
        return response['Messages']
    return None


#########################################################
def deletemessage(receipt_handle):

    # Delete received message from queue
    q.delete_message(
        QueueUrl=q_url,
        ReceiptHandle=receipt_handle
    )


#########################################################
def process_file(my_File, outgoing_url):

    spapi = sharepoint()
    customer = os.path.basename(my_File).partition(".")[0]
    misa = misapi()


    if(True):

        try:
            df = spapi.get_file_as_dataframe(my_File,
                                             converters={
                                                 'InvoiceNumber': str,
                                                 'INVOICENUMBER': str,
                                                 'PO_NUMBER': str,
                                                 'PONUMBER': str})
            # remove duplicate rows based on PACEID
            df.columns = df.columns.str.upper()
            df = df.drop_duplicates(subset='INVOICENUMBER', keep="last")

        except:
            data = ["INVALID FILE FORMAT"]
            df = pd.DataFrame(data, columns=['ERROR'])
            spapi.put_dataframe_to_file_formated(df, outgoing_url, customer + ".xlsx")

        # print("\n\n *********** INCOMING ({}) ************** ".format(os.path.basename(my_File)))
        # print(df.to_string())

        extravouchers = []
        index = -1
        for index, row in df.iterrows():

            data = misa.getvoucher(row['INVOICENUMBER'] + "]", customer)

            # print(len(data))
            if len(data) == 0:
                # df.at[index, 'ROW_UPDATED_TIME'] = datetime.utcnow()
                df.at[index, 'NOTES'] = 'INVOICE NOT FOUND'
                df.at[index, 'ON STATEMENT'] = "Yes"
                df.at[index, 'UNBILLED RECEIVING'] = "No"
                df.at[index, 'LOADED NOT PAID'] = "No"
            elif len(data) == 1:
                data = data[0]
                df.at[index, 'VENDOR NUMBER'] = data['vendorno']
                df.at[index, 'ON STATEMENT'] = "Yes"
                df.at[index, 'UNBILLED RECEIVING'] = "No"
                df.at[index, 'LOADED NOT PAID'] = "No"
                df.at[index, 'CHECK NUMBER'] = data['checknumber']
                df.at[index, 'CHECK DATE'] = data['checkdate']
                df.at[index, 'ANTICIPATED CHECK DATE'] = data['anticipatedcheckdate']
                df.at[index, 'VENDOR NAME'] = data['vendorname']
                df.at[index, 'INVOICE DATE'] = data['invoicedate']
                df.at[index, 'INVOICE AMOUNT'] = data['invoiceamount']
                df.at[index, 'MONTH YEAR'] = data['monthyear']
                df.at[index, 'DATE RECEIVED'] = data['datereceived']
                df.at[index, 'DISCOUNT'] = data['discount']
                df.at[index, 'REQPAY DATE'] = data['reqpaydate']
                df.at[index, 'RECEIVING PO'] = data['ponumber']
                df.at[index, 'BATCH NUMBER'] = data['batchnumber']
                # df.at[index, 'ROW_UPDATED_TIME'] = datetime.utcnow()
            else:
                df.at[index, 'ON STATEMENT'] = "Yes"
                for voucher in data:
                    voucher['statementinvoice'] = row['INVOICENUMBER']

                    x = voucher['Id'].split(row['INVOICENUMBER'])
                    if len(x) == 2:
                        y = x[1]
                        if len(y) == 1 and not(y.isnumeric()):
                            extravouchers.append(voucher)

        for voucher in extravouchers:

            y = df.index[df['INVOICENUMBER'] == voucher['Id']].tolist()

            if y:
                loc = y[0]
            else:
                index = index + 1
                loc = index

            z = df.index[df['INVOICENUMBER'] == voucher['statementinvoice']].tolist()
            if z:
                loc = z[0] + .5

            # line = DataFrame({"onset": 30.0, "length": 1.3}, index=[3])
            # df2 = concat([df.iloc[:2], line, df.iloc[2:]]).reset_index(drop=True)

            df.at[loc, 'INVOICENUMBER'] = voucher['Id']
            df.at[loc, 'VENDOR NUMBER'] = voucher['vendorno']
            df.at[loc, 'ON STATEMENT'] = "Split"
            df.at[loc, 'UNBILLED RECEIVING'] = "No"
            df.at[loc, 'LOADED NOT PAID'] = "No"
            df.at[loc, 'CHECK NUMBER'] = voucher['checknumber']
            df.at[loc, 'CHECK DATE'] = voucher['checkdate']
            df.at[loc, 'ANTICIPATED CHECK DATE'] = voucher['anticipatedcheckdate']
            df.at[loc, 'VENDOR NAME'] = voucher['vendorname']
            df.at[loc, 'INVOICE DATE'] = voucher['invoicedate']
            df.at[loc, 'INVOICE AMOUNT'] = voucher['invoiceamount']
            df.at[loc, 'MONTH YEAR'] = voucher['monthyear']
            df.at[loc, 'DATE RECEIVED'] = voucher['datereceived']
            df.at[loc, 'DISCOUNT'] = voucher['discount']
            df.at[loc, 'REQPAY DATE'] = voucher['reqpaydate']
            df.at[loc, 'RECEIVING PO'] = voucher['ponumber']
            df.at[loc, 'BATCH NUMBER'] = voucher['batchnumber']

            df = df.sort_index().reset_index(drop=True)


        #see if prices of changed
        #df = add_price_match(df, outgoing_url, customer, spapi)

        # all receivings not invoiced 
        pos = misa.getreceivedpos(customer)
        for po in pos:

            x = df.index[df['PO_NUMBER'] == po['Id']].tolist()

            if x:
                loc = x[0]
            else:
                index = index + 1
                loc = index

            try:
                # print(po)
                df.at[loc, 'PO_NUMBER'] = po['Id']
                df.at[loc, 'RECEIVING PO'] = po['Id']
                df.at[loc, 'PO DATE'] = po['podate']
                if po['invoice']:
                    df.at[loc, 'INVOICENUMBER'] = po['invoice']
                df.at[loc, 'REQDATE'] = po['reqdate']
                df.at[loc, 'VENDOR NUMBER'] = po['vendornum']
                df.at[loc, 'RECIEVED DATE'] = po['recdate']
                df.at[loc, 'RECEIVED AMOUNT'] = po['receivedamount']
                df.at[loc, 'TOTITEMS RECEIVED'] = po['totitemsreceived']
                # df.at[loc, 'ROW_UPDATED_TIME'] = datetime.utcnow()
                df.at[loc, 'UNBILLED RECEIVING'] = "Yes"
                if (loc == index):
                    df.at[loc, 'ON STATEMENT'] = "No"
                    df.at[loc, 'LOADED NOT PAID'] = "No"

            except:
                # df.at[loc, 'ROW_UPDATED_TIME'] = datetime.utcnow()
                df.at[loc, 'NOTES'] = 'UNKNOWN ERROR'
                df.at[loc, 'UNBILLED RECEIVING'] = "Yes"
                if (loc == index):
                    df.at[loc, 'ON STATEMENT'] = "No"
                    df.at[loc, 'LOADED NOT PAID'] = "No"

        # vouchers with no checks
        vouchers = misa.getvouchers_nocheck(customer)
        for voucher in vouchers:

            x = df.index[df['PO_NUMBER'] == voucher['ponumber']].tolist()
            y = df.index[df['INVOICENUMBER'] == voucher['Id']].tolist()

            if x:
                loc = x[0]
            elif y:
                loc = y[0]
            else:
                index = index + 1
                loc = index

            try:
                if voucher['ponumber']:
                    df.at[loc, 'PO_NUMBER'] = voucher['ponumber']
                if voucher['Id']:
                    df.at[loc, 'INVOICENUMBER'] = voucher['Id']
                df.at[loc, 'ANTICIPATED CHECK DATE'] = voucher['anticipatedcheckdate']
                df.at[loc, 'RECEIVING PO'] =  voucher['ponumber']
                df.at[loc, 'VENDOR NUMBER'] = voucher['vendorno']
                df.at[loc, 'VENDOR NAME'] = voucher['vendorname']
                df.at[loc, 'INVOICE DATE'] = voucher['invoicedate']
                df.at[loc, 'INVOICE AMOUNT'] = voucher['invoiceamount']
                df.at[loc, 'MONTH YEAR'] = voucher['monthyear']
                df.at[loc, 'DATE RECEIVED'] = voucher['datereceived']
                df.at[loc, 'DISCOUNT'] = voucher['discount']
                df.at[loc, 'REQPAY DATE'] = voucher['reqpaydate']
                df.at[loc, 'BATCH NUMBER'] = voucher['batchnumber']
                # df.at[loc, 'ROW_UPDATED_TIME'] = datetime.utcnow()
                df.at[loc, 'LOADED NOT PAID'] = "Yes"
                if (loc == index):
                    df.at[loc, 'UNBILLED RECEIVING'] = "No"
                    df.at[loc, 'ON STATEMENT'] = "No"
            except:
                # df.at[loc, 'ROW_UPDATED_TIME'] = datetime.utcnow()
                df.at[loc, 'NOTES'] = 'UNKNOWN ERROR'
                df.at[loc, 'LOADED NOT PAID'] = "Yes"
                if (loc == index):
                    df.at[loc, 'UNBILLED RECEIVING'] = "No"
                    df.at[loc, 'ON STATEMENT'] = "No"

    else:
        data = ["INVALID CUSTOMER NAME"]
        df = pd.DataFrame(data, columns=['ERROR'])


    df = df.replace(r'^\s*$', np.nan, regex=True)

    # print("\n ********************* OUTGOING ********************* ")
    # print(df.to_string())
    try:
        if 'INVOICE_DATE' in df:
            df['INVOICE_DATE'] = pd.to_datetime(df['INVOICE_DATE'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    try:
        if 'REQPAY_DATE' in df:
            df['REQPAY_DATE'] = pd.to_datetime(df['REQPAY_DATE'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    try:
        if 'RECIEVED_DATE' in df:
            df['RECIEVED_DATE'] = pd.to_datetime(df['RECIEVED_DATE'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    try:
        if 'PO_DATE' in df:
            df['PO_DATE'] = pd.to_datetime(df['PO_DATE'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    try:
        if 'DATE_RECEIVED' in df:
            df['DATE_RECEIVED'] = pd.to_datetime(df['DATE_RECEIVED'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    try:
        if 'REQDATE' in df:
            df['REQDATE'] = pd.to_datetime(df['REQDATE'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    try:
        if 'CHECK_DATE' in df:
            df['CHECK_DATE'] = pd.to_datetime(df['CHECK_DATE'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    try:
        if 'ANTICIPATED_CHECK_DATE' in df:
            df['ANTICIPATED_CHECK_DATE'] = pd.to_datetime(df['ANTICIPATED_CHECK_DATE'],infer_datetime_format=False, format='%m/%d/%y', errors='ignore').dt.date
    except:
        pass

    # print("\n ********************* OUTGOING ********************* ")
    # print(df.to_string())

    spapi.put_dataframe_to_file_formated(df, outgoing_url, customer + ".xlsx")



#########################################################
def lambda_handler(event, context):

    incoming_url = "/personal/sharepointfilesharesvc_pacesupply_com/Documents/InvoiceFiles/Incoming"
    outgoing_url = "/personal/sharepointfilesharesvc_pacesupply_com/Documents/InvoiceFiles/Outgoing"

    # check if records are passed in by event
    try:
        event
        # print(event)
    except NameError:
        event = None

    # process file directly passed in
    if os.environ.get('filename'):
        print(os.environ.get('filename'))
        process_file(incoming_url + "/" + os.environ.get('filename'), outgoing_url)

        return {
            'statusCode': 200,
            'body': os.environ.get('filename')
        }

    else:

        messages = None
        if event and "Records" in event:
            messages = event['Records']
        else:
            messages = getmessage()

        if messages:
            for message in messages:
                filename = None
                if "MessageAttributes" in message:
                    attributes = message['MessageAttributes']
                    filename = attributes['FileName']['StringValue']
                    receipt_handle = message['ReceiptHandle']
                elif "messageAttributes" in message:
                    attributes = message['messageAttributes']
                    filename = attributes['FileName']['stringValue']
                    receipt_handle = message['receiptHandle']

                if filename:
                    # print(message)
                    print(filename)
                    process_file(incoming_url + "/" + filename, outgoing_url)
                    deletemessage(receipt_handle)

            return {
                'statusCode': 200,
                'body': messages
            }

    print("No messages found")
    return {
        'statusCode': 200,
        'body': "No messages found"
    }

if __name__ == "__main__":

    lambda_handler(None, None)

