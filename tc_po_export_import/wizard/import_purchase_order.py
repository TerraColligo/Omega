import xlrd
from odoo import fields, models, api,_
import base64
from odoo.exceptions import Warning, ValidationError
from odoo.exceptions import UserError
from datetime import datetime
import sys
import logging
from io import  BytesIO
try:
    import  xlwt
    from    xlwt import Borders
except ImportError:
    xlwt = None

_logger=logging.getLogger(__name__)

PY3 = sys.version_info >= (3,0)

if PY3:
    basestring = str
    long = int
    xrange = range
    unicode = str
    

class ImportPurchaseOrder(models.TransientModel):
    _name = "tc.import.purchase.order.xls"
    
    choose_file = fields.Binary(string='Choose File',help="File extention Must be XLS or XLSX file",copy=False)
    datas = fields.Binary(help="store binary data")
    file_name = fields.Char(string='Filename',size=512)    
    mismatch_log_id = fields.Many2one('import.orders.mismatch.log',string='Mismatch Log')    
    
    def read_file(self, file_name, choose_file):
        try:
            file_path = '/tmp/%s_%s' % (datetime.strftime(datetime.now(), '%Y%m%d%H%M%S%f'), file_name)
            fp = open(file_path, 'wb')
            fp.write(base64.decodestring(choose_file))
            fp.close()
            xl_workbook = xlrd.open_workbook(file_path)
            worksheet = xl_workbook.sheet_by_index(0)

        except Exception as e:
            error_value = str(e)
            raise ValidationError(error_value)
        return worksheet
    
    def get_header(self, worksheet):
        try:
            column_header = {}
            for col_index in xrange(worksheet.ncols):
                value = worksheet.cell(0, col_index).value
                column_header.update({col_index: value})
        except Exception as e:
            error_value = str(e)
            raise ValidationError(error_value)

        return column_header
    
    @api.multi
    def validate_fields(self, fieldnames):
        '''
            This import pattern requires few fields default, so check it first whether it's there or not.
        '''
        headers = ['External Id','Vendor Name','Company Name','Product Name','Order Lines/Description','Order Lines/Product Unit of Measure','Order Lines/Quantity','Order Lines/Unit Price']
        missing = []
        for field in headers:
            if field not in fieldnames:
                missing.append(field)
            
        if len(missing) > 0:
            raise ValidationError("Please Provide All the Required Fields in file, Missing Fields => %s." %(missing))
        
        return True
    
    def fill_dictionary_from_file(self, worksheet, column_header):
        try:
            data = []
            for row_index in range(1, worksheet.nrows):
                sheet_data = {}
                for col_index in xrange(worksheet.ncols):
                    sheet_data.update({column_header.get(col_index): worksheet.cell(row_index, col_index).value})
                data.append(sheet_data)
        except Exception as e:
            error_value = str(e)
            raise ValidationError(error_value)

        return data
    
    @api.multi
    def create_mismatch_log(self, msg="Import Purchase Order", to_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
        log_obj=self.env['import.orders.mismatch.log']
        log_id=log_obj.create({'log_date':to_date,'message':msg,'type':'import'})
        return log_id
    
    @api.multi
    def create_mismatch_log_line(self, msg, log_id):
        log_line_obj=self.env['import.orders.mismatch.log.line']
        log_line_obj.create({
                            'job_id' : log_id.id,
                            'message':msg 
                        })
    
    @api.multi
    def validate_data(self, purchase_data= []):
        purchase_obj = self.env['purchase.order']
        product_obj = self.env['product.product']
        row_number = 1
        po_name = ''
        purchase_list = []
        for data in purchase_data:
            external_id = data.get('External Id')
            invalid_data = []
            row_number += 1
            barcode = data.get('Barcode')
            if not barcode:
                msg = "Please Enter the Barcode Number of row number %s"%(row_number)
                invalid_data.append(msg)
                
            product_name = data.get('Product Name')
            if not product_name:
                msg = "Please Enter the Product name of row number %s"%(row_number)
                invalid_data.append(msg)
            
            if  barcode == '' :
                barcode =''
            elif  type(barcode) == float:
                barcode = ("%s"%(int(barcode))).strip() if barcode else ''
            else:
                barcode = str(barcode).strip()

            product_name = product_name.strip()
            product_id = product_obj.search([('name','=',product_name),('barcode','=',barcode)],limit=1)
            #product_id = product_obj.search([('name','=',product_name)],limit=1)            
            if not product_id:
                msg = 'Product not found  Related Barcode number %s and Product name %s !! Row Number : %s '%(barcode,product_name,row_number)
                invalid_data.append(msg)
            
            partner = str(data.get('Vendor Name',''))
            if not partner:
                msg = "Please Enter the Partner name of row number %s"%(row_number)
                invalid_data.append(msg)
            
            partner = partner.strip()
            partner_obj = self.env['res.partner'].search([('name','=',partner)],limit=1)
            if not partner_obj:
                length=len(partner)
                if length > 5:
                    partner = partner[0:5]
                elif length <= 3:
                    partner = partner[0:2]
                elif length > 7:
                    partner = partner[0:5]
                partner_obj = self.env['res.partner'].search([('name','ilike',partner)],limit=1)
                if not partner_obj:
                    msg = 'not found related Partner name %s of Row Number : %s '%(partner,row_number)
                    invalid_data.append(msg)

                
            company = data.get('Company Name','')
            if  not company:
                msg = "Please Enter the Company name of row number %s"%(row_number)
                invalid_data.append(msg)
            
            company = company.strip()
            company_obj = self.env['res.company'].search([('name','=',company)],limit=1)
            if not company_obj:
                currecy_obj = self.env['res.currency'].search([('name','=','USD')])
                vals = {'name':company,'currency_id':currecy_obj.id}
                company_obj = self.env['res.company'].create(vals)
                
            uom = data.get('Order Lines/Product Unit of Measure')
            if not uom:
                msg = "Not Found related Unit Of Measure of row number %s"%(row_number)
                invalid_data.append(msg)
                
            uom = uom.strip()
            product_uom_obj = self.env['product.uom'].search([('name','=',uom)],limit=1)
            if product_uom_obj and product_id:
                if product_uom_obj.name != product_id.uom_id.name:
                    msg = 'Does not match Product Uom %s of Row Number : %s '%(uom,row_number)
                    invalid_data.append(msg)
            if not product_uom_obj:
                msg = 'not found related Unit Of Measure %s of Row Number : %s '%(uom,row_number)
                invalid_data.append(msg)
            
            description = data.get('Order Lines/Description','')
            tax_ids = self.env.ref('tc_po_export_import.tasa_16_percent').ids
            if len(invalid_data) == 0:       
                po_name = external_id
                purchase_order_id = self.env['purchase.order'].search([('external_id','=',po_name),('processed','=',True)])                
                if not purchase_order_id:
                    if len(purchase_list) > 0:
                        message = "no se pueden importar Rfq múltiple en el archivo. \n Multiple Rfq in the File unable to import"           
                        raise UserError(_(message))
                        
                    order_vals = {
                            'partner_id':partner_obj.id,
                            'company_id':company_obj.id,
                            'currency_id':company_obj.currency_id.id,
                            'date_order':datetime.now()
                    }
                    new_record = purchase_obj.new(order_vals)
                    new_record.onchange_partner_id() # Return Pricelist- Payment terms- Invoice address- Delivery address
                    order_vals = purchase_obj._convert_to_write({name: new_record[name] for name in new_record._cache})
                    order_vals.update({
                        'date_order':datetime.now(),
                        'user_id':self.env.user.id,
                        'state':'draft',
                        'currency_id':company_obj.currency_id.id,
                        'external_id':po_name,
                        'processed':True
                        })
                    purchase_order_id = self.env['purchase.order'].create(order_vals)
                    purchase_list.append(purchase_order_id.id)
                purchase_order_line = self.env['purchase.order.line'] 
                order_line = {
                    'order_id':purchase_order_id.id,
                    'name':description,
                    'product_id':product_id.id,
                    'name':product_id.name,
                    'company_id':company_obj.id
                }
                new_order_line = purchase_order_line.new(order_line)
                new_order_line.onchange_product_id()
                order_line = purchase_order_line._convert_to_write({name:new_order_line[name] for name in new_order_line._cache})
                order_line.update({
                    'product_qty':data.get('Order Lines/Quantity',1.0),
                    'price_unit':data.get('Order Lines/Unit Price',''),
                    'product_uom':product_uom_obj.id or product_id.uom_id.id,
                    'state':'draft',
                    'taxes_id':[(6,0,tax_ids)]
                    })    
                purchase_order_line.create(order_line)
            else:
                for error_msg in invalid_data:
                    self.create_mismatch_log_line(error_msg, self.mismatch_log_id)
        
        po_obj = self.env['purchase.order'].browse(purchase_list)
        po_obj.write({'processed':False})
    
    def validate_process(self):
        '''
            Validate process by checking all the conditions and return back with sale order object
        '''   
        if not self.choose_file:
            raise ValidationError('Please select file to process...')

    @api.multi
    def tc_import_purchase_order(self):
        if self.file_name and self.file_name[-3:] != 'xls' and self.file_name[-4:] != 'xlsx': 
            raise Warning("Please provide only .xls OR .xlsx Formated file to import forecasted sales!!!")
        to_date=datetime.now()
        self.mismatch_log_id = self.create_mismatch_log(to_date=to_date)
        try:
            worksheet = self.read_file(self.file_name,self.choose_file)
            column_header = self.get_header(worksheet)
            file_header = column_header.values()
            if self.validate_fields(file_header):
                purchase_data = self.fill_dictionary_from_file(worksheet,column_header)
                self.validate_data(purchase_data)                
                self._cr.commit()
        except Exception as e:
            self.validate_process()
            self.mismatch_log_id.write({'message' :str(e),'company_id':self.env.user.company_id.id})
            raise Warning(str(e))
        if not self.mismatch_log_id.transaction_line_ids:
            self.mismatch_log_id.write({'company_id':self.env.user.company_id.id,'message' : 'Purchase Orders Imported Sucessfully'})
