from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
from io import  BytesIO
try:
    import  xlwt
    from    xlwt import Borders
except ImportError:
    xlwt = None
    
class ExportPurchaseOrder(models.TransientModel):
    _name = 'tc.export.purchase.order'
    
    datas = fields.Binary('File')
    
    @api.multi
    def export_purchased_stock_to_xls(self):
        purchase_obj=self.env['purchase.order']
        purchase_ids=self._context.get('active_ids')
        if len(purchase_ids) > 1:
            raise UserError(_('Más que un RFQ seleccionada.Imposible para exportar. \n More Than One RFQ Selected Impossible to Export') )
        workbook = xlwt.Workbook()
        borders = Borders()
        borders.left,borders.right,borders.top,borders.bottom = Borders.HAIR,Borders.HAIR,Borders.HAIR,Borders.HAIR
        right_border = Borders()
        right_border.right = Borders.HAIR
        
        worksheet = workbook.add_sheet("Purchase Order",cell_overwrite_ok=True)
        worksheet.panes_frozen = True
        worksheet.remove_splits = True
        worksheet.horz_split_pos = 1
        header_bold = xlwt.easyxf("font: bold on, height 250; pattern: pattern solid, fore_colour black;alignment: horizontal center")
        header_title = xlwt.easyxf("font: bold on, height 300; pattern: pattern solid, fore_colour gray25;alignment: horizontal center")
        
        plain_style = xlwt.easyxf()
        plain_style.borders=right_border
         
        header_title.borders=borders
        header_bold.borders=borders
        
        def get_width(num_characters):
            return int((1+num_characters) * 256)
        
        headers = ['External Id','Vendor Name','Company Name','Product Name','Barcode','Order Lines/Description','Order Lines/Product Unit of Measure','Order Lines/Quantity','Order Lines/Unit Price']
        
        column = 0
        for header in headers:
            worksheet.write(0,column,header,header_bold)
            if len(header) > 8 :
                worksheet.col(column).width = get_width(len(header)+4)
            column+=1
        row = 1
        
        purchase_orders=purchase_obj.search([('id','in',purchase_ids)])
        purchase_order_obj = purchase_orders.filtered(lambda po:po.state=='draft')
        
        for po in purchase_order_obj:
            seq = po.name
            po_exteranal_id = '_export_purchase_order_'+seq
            for order_line in po.order_line:
                vendor_name = order_line.order_id.partner_id.name
                company = order_line.order_id.company_id.name
                product_name = order_line.product_id.name
                barcode = order_line.product_id.barcode or ''
                discription = order_line.name
                product_uom = order_line.product_uom.name        
                qty = order_line.product_qty
                price_unit = order_line.price_unit
            
                worksheet.write(row,0,po_exteranal_id)
                worksheet.col(0).width = get_width(len(po_exteranal_id)+4)
                worksheet.write(row,1,vendor_name)
                worksheet.col(1).width = get_width(len(vendor_name)+4)
                worksheet.write(row,2,company)
                worksheet.write(row,3,product_name)
                worksheet.col(3).width = get_width(len(product_name)+4)
                worksheet.write(row,4,barcode)
                worksheet.write(row,5,discription)
                worksheet.write(row,6,product_uom)
                worksheet.write(row,7,qty)
                worksheet.write(row,8,price_unit)
            
                row += 1
        if purchase_order_obj:
            
            fp = BytesIO()
            workbook.save(fp)
            fp.seek(0)
            report_data_file = base64.encodestring(fp.read())
            fp.close()
            self.write({'datas':report_data_file})
            
            return {
                'type' : 'ir.actions.act_url',
                'url':   'web/content/?model=tc.export.purchase.order&field=datas&download=true&id=%s&filename=ftq_export_purchase_order-%s.xls'%(self.id,purchase_orders.name),
                'target': 'new',
                }
            
