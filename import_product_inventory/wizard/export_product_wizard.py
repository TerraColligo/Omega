# -*- coding: utf-8 -*-
from odoo import models,api,fields
from odoo.exceptions import Warning
from datetime import datetime
#from cStringIO import StringIO
import uuid
import io
from odoo.tools.misc import xlwt
from itertools import product
import base64
# try:
#     import xlsxwriter
# except ImportError:
#     xlsxwriter = None
    
class export_product_with_inventory_file(models.TransientModel):
    _name ='export.product.with.inventory.file'
    
    file_data = fields.Binary("File Data")
        
    @api.multi
    def export_products(self):
        
#         if xlsxwriter==None:
#             raise Warning(_("Unable to load Python module \"{modname}\" \n Install it by command : sudo pip install xlsxwriter").format(modname='xlsxwriter'))

        #fp = StringIO()
        #workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        
        filename = 'products_%s.xls'%(datetime.today().strftime("%Y_%m_%d_%H_%M_%S"))
        workbook = xlwt.Workbook()
        bold = xlwt.easyxf("font: bold on;")
        
#         header_format_without_color = workbook.add_format({
#             'border': 1,
#             'bold': True,
#             'text_wrap': True,
#             'valign': 'vcenter',
#             'indent': 1,
#         })
        quant_obj = self.env['stock.quant']
        products = self.env['product.product'].search([])
        company_id = self.env.user.company_id.id
        
        #worksheet = workbook.add_worksheet('Products')
        worksheet = workbook.add_sheet('Products')
        
        headers = ['id','categ_id/name','name','barcode','default_code','unit_of_measurement','type','route_ids/id','purchase_ok','sale_ok','standard_price','lst_price','seller_ids/name/name']
        warehouse_ids = []
        product_obj = self.env['product.product']
        product_ids = products.ids
        product_inventory_by_wh = {}
        for warehouse in self.env['stock.warehouse'].search([('company_id','=',company_id)]):
            headers.append(warehouse.code)
            #For faster quantity calculation, used quary.
            domain_quant_loc, domain_move_in_loc, domain_move_out_loc = product_obj._get_domain_locations_new([warehouse.view_location_id.id])
            domain_quant = [('product_id', 'in', product_ids)] + domain_quant_loc
            query = quant_obj._where_calc(domain_quant)
            from_clause, where_clause, where_clause_params = query.get_sql()
            where_str = where_clause and (" WHERE %s" % where_clause) or ''
            
            query_str = 'SELECT product_id, sum(quantity) as quantity FROM '+ from_clause + where_str + ' group by product_id'
            self._cr.execute(query_str, where_clause_params)
            res = dict(self._cr.fetchall())
            product_inventory_by_wh.update({warehouse.id:res})
            warehouse_ids.append(warehouse.id)
            
        product_xml_ids = dict(self.__ensure_xml_id_custom(products))
        sellers_mapping_dict = {}
        for i,header in enumerate(headers):
            worksheet.write(0, i, header, bold)
            worksheet.col(i).width = 8000 # around 220 pixels
        
        def splittor(rs):
            """ Splits the self recordset in batches of 1000 (to avoid
            entire-recordset-prefetch-effects) & removes the previous batch
            from the cache after it's been iterated in full
            """
            for idx in range(0, len(rs), 1000):
                sub = rs[idx:idx+1000]
                for rec in sub:
                    yield rec
                rs.invalidate_cache(ids=sub.ids)
        row_index = 1 
        for product in splittor(products):
            if product.route_ids:
                xml_ids = [xid for _, xid in self.__ensure_xml_id_custom(product.route_ids)]
                route_ids = ','.join(xml_ids) or False
            else:
                route_ids=''
            i=0
            worksheet.write(row_index, i, product_xml_ids.get(product.id))
            i +=1
            worksheet.write(row_index, i, product.categ_id.name)
            i +=1
            worksheet.write(row_index, i, product.name)
            i +=1
            worksheet.write(row_index, i, product.barcode or '')
            i +=1
            worksheet.write(row_index, i, product.default_code or '')
            i +=1
            worksheet.write(row_index, i, product.uom_id.name)
            i +=1
            worksheet.write(row_index, i, product.type)
            i +=1
            worksheet.write(row_index, i, route_ids)
            i +=1
            worksheet.write(row_index, i, product.purchase_ok)
            i +=1
            worksheet.write(row_index, i, product.sale_ok)
            i +=1
            worksheet.write(row_index, i, product.standard_price)
            i +=1
            worksheet.write(row_index, i, product.lst_price)
            i +=1
            seller_xml_ids = []
            for seller in product.seller_ids.mapped('name'):
                if seller.id not in sellers_mapping_dict:
                    xml_rec = self.__ensure_xml_id_custom(seller)
                    sellers_mapping_dict.update({seller.id: xml_rec and xml_rec[0][1] or False})
                seller_xml_ids.append(sellers_mapping_dict.get(seller.id) or '')
            
            worksheet.write(row_index, i, ','.join(seller_xml_ids))
            i +=1
            
            for warehouse_id in warehouse_ids:
                worksheet.write(row_index, i, product_inventory_by_wh[warehouse_id].get(product.id,0.0))
                #worksheet.write(row_index, i, product.with_context(warehouse=warehouse_id).qty_available)
                i +=1
            row_index += 1
#         workbook.close()
#         fp.seek(0)
#         data = fp.read()
#         fp.close()
        
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        
        self.write({'file_data':base64.b64encode(data)})
        return {
            'type' : 'ir.actions.act_url',
            'url':   '/web/binary/savefile_custom?model=%s&field=file_data&id=%s&file_name=%s&content_type="application/vnd.ms-excel"' % (self._name, self.id,filename),
            'target':'self',
            }
        
    def __ensure_xml_id_custom(self, records):
        """ Create missing external ids for records in ``self``, and return an
            iterator of pairs ``(record, xmlid)`` for the records in ``self``.

        :rtype: Iterable[Model, str | None]
        """
        
        if not records:
            return iter([])
        modname = '__export__'

        cr = self.env.cr
        cr.execute("""
            SELECT res_id, CASE WHEN length(module)>0 THEN module || '.' || name ELSE name END AS external_id   
            FROM ir_model_data
            WHERE model = %s AND res_id in %s
        """, (records._name, tuple(records.ids)))
        
        result = cr.fetchall()
        if len(result)==len(records):
            return result
        
        cr.execute("""
            SELECT res_id, module, name
            FROM ir_model_data
            WHERE model = %s AND res_id in %s
        """, (records._name, tuple(records.ids)))
        xids = {
            res_id: (module, name)
            for res_id, module, name in cr.fetchall()
        }
        def to_xid(record_id):
            (module, name) = xids[record_id]
            return ('%s.%s' % (module, name)) if module else name

        # create missing xml ids
        missing = records.filtered(lambda r: r.id not in xids)
        if not missing:
            return (
                (record.id, to_xid(record.id))
                for record in records
            )
        xids.update(
            (r.id, (modname, '%s_%s_%s' % (
                r._table,
                r.id,
                uuid.uuid4().hex[:8],
            )))
            for r in missing
        )
        fields = ['module', 'model', 'name', 'res_id']
        cr.copy_from(io.StringIO(
            u'\n'.join(
                u"%s\t%s\t%s\t%d" % (
                    modname,
                    record._name,
                    xids[record.id][1],
                    record.id,
                )
                for record in missing
            )),
            table='ir_model_data',
            columns=fields,
        )
        self.env['ir.model.data'].invalidate_cache(fnames=fields)

        return list(
            (record.id, to_xid(record.id))
            for record in records
        )
