# -*- coding: utf-8 -*-
from odoo import models,fields, api, tools
import json
import logging
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import base64
import requests
from psycopg2 import IntegrityError
from odoo.tools.safe_eval import safe_eval
_logger = logging.getLogger(__name__)


class ProductImportBatch(models.Model):
    _name = 'product.import.batch'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char('Batch Name')
    data = fields.Text('Batch Data',default="{}")
    sheet_name = fields.Char('Sheet Name')
    state = fields.Selection([('pending','Pending'),('imported','Imported'),('failed','Failed')],string='Status',default='pending')
    inventory_option = fields.Selection([('ADD','ADD'),('SET','SET'),('archive','Archive'),('archive_rename','Archive & Rename')],string="Inventory Option")

    @api.multi
    def action_import_product_data(self):
        product_obj = self.env['product.product']
        category_obj = self.env['product.category']
        uom_obj = self.env['product.uom']
        warehouse_obj = self.env['stock.warehouse']
        inventory_obj = self.env['stock.inventory']
        pos_category_obj = self.env['pos.category']
        route_mapping_dict = {}
        supplier_tax_mapping_dict = {}
        customer_tax_mapping_dict = {}
        sat_mapping_dict = {}
        sellers_mapping_dict = {}
        #To manange savepoiunt, we used ids instead of direct browsable record.
        ids = self.ids
        cr = self._cr
        product_columns = ['id','Archive','invoice_policy','purchase_method','categ_id/name','pos_categ_id/name','available_in_pos','name','barcode','default_code','unit_of_measurement','uom_po_id','l10n_mx_edi_code_sat_id','supplier_taxes_id','taxes_id','type','route_ids/id','purchase_ok','sale_ok','standard_price','lst_price','seller_ids/name/name','image_medium']
        category_mapping_dict = {}
        uom_mapping_dict = {}
        po_uom_mapping_dict = {}
        location_id_dict = {}
        company_id = self.env.user.company_id.id
        uid = self._uid
        category_mapping_dict = dict((c.complete_name,c.id) for c in category_obj.search([]))
        pos_category_mapping_dict = dict((c.complete_categ_name,c.id) for c in pos_category_obj.search([]))

        for batch_id in ids:
            try:
                inventory_line_vals = {}
                location_id_inventory_dict = {}
                inventory_columns = []
                batch = self.browse(batch_id)
                inventory_option = batch.inventory_option
                cr.execute('SAVEPOINT model_batch_save')
                try:
                    data = json.loads(batch.data)
                except Exception as e:
                    continue
                for product in data:
                    if not inventory_columns:
                        inventory_columns = list(set(product.keys())-set(product_columns))

                    active = product.get('Archive')
                    category_name = product.get('categ_id/name')
                    pos_category_name = product.get('pos_categ_id/name')
                    available_in_pos = product.get('available_in_pos')
                    invoice_policy = product.get('invoice_policy')
                    purchase_method = product.get('purchase_method')
                    uom_name = product.get('unit_of_measurement')
                    image_medium = product.get('image_medium')
                    uom_po_name = product.get('uom_po_id')
                    sat_id = product.get('l10n_mx_edi_code_sat_id')
                    supplier_taxes = product.get('supplier_taxes_id')
                    customer_taxes = product.get('taxes_id')
                    #category_code = product.get('Cat Code')
                    default_code = product.get('default_code')
                    product_name = product.get('name')
                    product_type = product.get('type')
                    barcode = product.get('barcode') or False
                    routes = product.get('route_ids/id')
                    purchase_ok = product.get('purchase_ok')
                    sale_ok = product.get('sale_ok')
                    standard_price = product.get('standard_price')
                    lst_price = product.get('lst_price')
                    external_id = product.get('external_id','') or product.get('id','')
                    if category_name not in category_mapping_dict:
                        category_exist = category_obj.search([('name','=',category_name)],limit=1)
                        if not category_exist:
                            category_exist = category_obj.create({'name':category_name}) #,'category_code':category_code
                        category_mapping_dict.update({category_name:category_exist.id})
                    category_id = category_mapping_dict.get(category_name)

                    if pos_category_name and pos_category_name not in pos_category_mapping_dict:
                        pos_categories = pos_category_name.split(" / ")
                        pos_categories = list(map(str.strip, pos_categories))
                        pos_new_categ_list = pos_categories[:-1]

                        pos_top_category = pos_categories[0]
                        exist_pos_top_categories = pos_category_obj.search([('name','=',pos_top_category),('parent_id','=',False)])
                        if not exist_pos_top_categories:
                            exist_pos_top_categories = pos_category_obj.create({'name':pos_top_category})
                        top_pos_path_exist = exist_pos_top_categories.filtered(lambda x:x.complete_categ_name==pos_category_name)
                        if top_pos_path_exist:
                            pos_category_mapping_dict.update({top_pos_path_exist[0].complete_categ_name:top_pos_path_exist[0].id})
                        else:
                            path_exist = False
                            existed_pos_all_child_categories = pos_category_obj.search([('id','child_of', exist_pos_top_categories.ids)])
                            while pos_new_categ_list:
                                categ_path = " / ".join(pos_new_categ_list)
                                path_exist = existed_pos_all_child_categories.filtered(lambda x:x.complete_categ_name==categ_path)
                                if path_exist:
                                    path_exist = path_exist[0]
                                    break
                                pos_new_categ_list = pos_new_categ_list[:-1]
                            if not path_exist:
                                path_exist = exist_pos_top_categories[0]

                            parent_categ = path_exist
                            exist_category = parent_categ
                            for cat in pos_categories[len(path_exist.complete_categ_name.split(" / ")):]:
                                exist_category = pos_category_obj.create({'name':cat,'parent_id':parent_categ.id})
                                parent_categ = exist_category
                                if exist_category.complete_categ_name not in pos_category_mapping_dict:
                                    pos_category_mapping_dict.update({exist_category.complete_categ_name:exist_category.id})
                            else:
                                pos_category_mapping_dict.update({pos_category_name:exist_category.id})

                    pos_category_id = pos_category_mapping_dict.get(pos_category_name)

                    if uom_name and uom_name not in uom_mapping_dict:
                        uom_exist = uom_obj.search([('name','=',uom_name)],limit=1)
                        uom_mapping_dict.update({uom_name:uom_exist.id})
                    uom_id = uom_mapping_dict.get(uom_name)
                    if uom_po_name and uom_po_name not in po_uom_mapping_dict:
                        po_uom_exist = uom_obj.search([('name','=',uom_po_name)],limit=1)
                        po_uom_mapping_dict.update({uom_po_name:po_uom_exist.id})
                    po_uom_id = po_uom_mapping_dict.get(uom_po_name)
                    route_ids = []
                    if routes:
                        for route_ext_id in routes.split(','):
                            route_ext_id = route_ext_id.strip()
                            if route_ext_id not in route_mapping_dict:
                                route_record = self.env.ref(route_ext_id,False)
                                if route_record and route_record._name=='stock.location.route':
                                    route_mapping_dict.update({route_ext_id:route_record.id})
                                else:
                                    route_mapping_dict.update({route_ext_id:False})
                            route_id = route_mapping_dict.get(route_ext_id)
                            if route_id:
                                route_ids.append(route_id)
                    if sat_id:
                        sat_code = sat_id.strip()
                        if len(sat_code) == 7:
                            sat_code = '0' + str(sat_code)
                        elif len(sat_code) == 6:
                            sat_code = '00' + str(sat_code)
                        elif len(sat_code) == 5:
                            sat_code = '000' + str(sat_code)
                        elif len(sat_code) == 4:
                            sat_code = '0000' + str(sat_code)
                        sat_rec_id = self.env['l10n_mx_edi.product.sat.code'].search([('code', '=', sat_code)], limit=1).id
                        # sat_ext_id = sat_id.strip()
                        # if sat_ext_id not in sat_mapping_dict:
                        #     sat_record = self.env.ref(sat_ext_id,False)
                        #     if sat_record and sat_record._name=='l10n_mx_edi.product.sat.code':
                        #         sat_mapping_dict.update({sat_ext_id:sat_record.id})
                        #     else:
                        #         sat_mapping_dict.update({sat_ext_id:False})
                        # sat_rec_id = sat_mapping_dict.get(sat_ext_id)
                    supplier_tax_ids = []
                    if supplier_taxes:
                        for supplier_tax_ext_id in supplier_taxes.split(','):
                            supplier_tax_ext_id = supplier_tax_ext_id.strip()
                            supplier_tax_ids = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('name', '=', supplier_tax_ext_id)])
                            supplier_tax_ids = supplier_tax_ids.ids
                            # if supplier_tax_ext_id not in supplier_tax_mapping_dict:
                            #     supplier_tax_record = self.env.ref(supplier_tax_ext_id,False)
                            #     if supplier_tax_record and supplier_tax_record._name=='account.tax':
                            #         supplier_tax_mapping_dict.update({supplier_tax_ext_id:supplier_tax_record.id})
                            #     else:
                            #         supplier_tax_mapping_dict.update({supplier_tax_ext_id:False})
                            # supplier_tax_id = supplier_tax_mapping_dict.get(supplier_tax_ext_id)
                            # if supplier_tax_id:
                            #     supplier_tax_ids.append(supplier_tax_id)
                    customer_tax_ids = []
                    if customer_taxes:
                        for customer_tax_ext_id in customer_taxes.split(','):
                            customer_tax_ext_id = customer_tax_ext_id.strip()
                            customer_tax_ids = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('name', '=', customer_tax_ext_id)])
                            customer_tax_ids = customer_tax_ids.ids
                            # if customer_tax_ext_id not in customer_tax_mapping_dict:
                            #     customer_tax_record = self.env.ref(customer_tax_ext_id,False)
                            #     if customer_tax_record and customer_tax_record._name=='account.tax':
                            #         customer_tax_mapping_dict.update({customer_tax_ext_id:customer_tax_record.id})
                            #     else:
                            #         customer_tax_mapping_dict.update({customer_tax_ext_id:False})
                            # customer_tax_id = customer_tax_mapping_dict.get(customer_tax_ext_id)
                            # if customer_tax_id:
                            #     customer_tax_ids.append(customer_tax_id)
                    sellers = product.get('seller_ids/name/name')
                    seller_ids = []
                    if sellers:
                        for seller_ext_id in sellers.split(','):
                            seller_ext_id = seller_ext_id.strip()
                            if seller_ext_id not in sellers_mapping_dict:
                                seller_record = self.env.ref(seller_ext_id,False)
                                if seller_record and seller_record._name=='res.partner':
                                    sellers_mapping_dict.update({seller_ext_id:seller_record.id})
                                else:
                                    sellers_mapping_dict.update({seller_ext_id:False})
                            seller_id = sellers_mapping_dict.get(seller_ext_id)
                            if seller_id:
                                seller_ids.append((0,0,{'name':seller_id,'min_qty':1,}))
                    if product_type == 'Consumable':
                        product_type = 'consu'
                    elif product_type == 'Service':
                        product_type = 'service'
                    elif product_type == 'Stockable Product':
                        product_type = 'product'
                    if product_type not in ['consu','service','product']:
                        product_type = 'product'
                    product_vals = {
                        'name' : product_name,
                        'default_code' : default_code,
                        'type' : product_type,
                        'categ_id' : category_id,
                        'barcode' : barcode,
                        'purchase_ok':purchase_ok,
                        'sale_ok' : sale_ok,
                        'standard_price' : standard_price,
                        'lst_price' : lst_price,
                        'available_in_pos' : available_in_pos,
                        'invoice_policy': invoice_policy,
                        'purchase_method': purchase_method,
                        }
                    if image_medium:
                        parsed_url = urlparse(image_medium)
                        if parsed_url.scheme:
                            try:
                                content = base64.b64encode(requests.get(image_medium,headers=request_header).content)
                                product_vals['image_medium'] = content
                            except Exception as e:
                                pass
                    if pos_category_id:
                        product_vals.update({'pos_categ_id' : pos_category_id})
                    if route_ids:
                        product_vals.update({'route_ids' : [(6,0,route_ids)]})
                    if sat_rec_id:
                        product_vals.update({'l10n_mx_edi_code_sat_id' : sat_rec_id})
                    if supplier_tax_ids:
                        product_vals.update({'supplier_taxes_id' : [(6,0,supplier_tax_ids)]})
                    if customer_tax_ids:
                        product_vals.update({'taxes_id' : [(6,0,customer_tax_ids)]})
                    if seller_ids:
                        product_vals.update({'seller_ids' : seller_ids})
                    if uom_id:
                        product_vals.update({'uom_id' : uom_id,'uom_po_id':uom_id})
                    if po_uom_id:
                        product_vals.update({'uom_po_id' : po_uom_id})
                    if inventory_option == 'archive' and active:
                        if active == '0':
                            product_vals.update({'active' : True})
                        elif active == '1':
                            product_vals.update({'active' : False})
                    if inventory_option == 'archive_rename' and active:
                        if active == '0':
                            product_vals.update({'active' : True, 'name': product_name})
                        elif active == '1':
                            product_vals.update({'active' : False, 'name': product_name})
                    product_exist=False
                    if external_id:
                        product_exist = self.env.ref(external_id,False)
                    if not product_exist and default_code:
                        product_exist = product_obj.sudo().search(['|', ('active', '=', False), ('active', '=', True), ('default_code','=',default_code), ('default_code','=',default_code)],limit=1)

                    try:
                        cr.execute('SAVEPOINT model_batch_product_save')
                        if product_exist:
                            product_exist.write(product_vals)
                            if product_vals.get('image_medium') and len(product_exist.product_tmpl_id.product_variant_ids)==1:
                                resized_images = tools.image_get_resized_images(product_vals.get('image_medium'), return_big=True, avoid_resize_medium=True)
                                product_exist.product_tmpl_id.write({'image_medium' : resized_images['image_medium'], 'image_small': resized_images['image_small'], 'image' : resized_images['image']})
                        else:
                            product_exist = product_obj.create(product_vals)
                        self.get_create_xml_id(product_exist, external_id)
                        cr.execute('RELEASE SAVEPOINT model_batch_product_save')
                    except IntegrityError as e:
                        cr.execute('ROLLBACK TO SAVEPOINT model_batch_product_save')
                        if 'duplicate key value violates unique constraint "product_product_barcode_uniq"' in e.message:
                            cr.execute('SAVEPOINT model_batch_product_save')
                            product_vals.pop('barcode')
                            if product_exist:
                                product_exist.write(product_vals)
                                if product_vals.get('image_medium') and len(product_exist.product_tmpl_id.product_variant_ids)==1:
                                    resized_images = tools.image_get_resized_images(product_vals.get('image_medium'), return_big=True, avoid_resize_medium=True)
                                    product_exist.product_tmpl_id.write({'image_medium' : resized_images['image_medium'], 'image_small': resized_images['image_small'], 'image' : resized_images['image']})
                            else:
                                product_exist = product_obj.create(product_vals)
                            self.get_create_xml_id(product_exist, external_id)
                            cr.execute('RELEASE SAVEPOINT model_batch_product_save')
                    for column_name in inventory_columns:
                        product_qty = product.get(column_name)
                        code = column_name.strip()
                        if code not in location_id_dict:
                            warehouse = warehouse_obj.search([('code','=',code),('company_id','=',company_id)],limit=1)
                            location_id_dict.update({code:warehouse.lot_stock_id.id})
                        location_id = location_id_dict.get(code)
                        if product_qty and type(product_qty) in [str,bytes]:
                            product_qty = safe_eval(product_qty)
                        if location_id and type(product_qty) in [float,int] and product_qty>=0: #and product_qty not in [None,False,'']
                            if location_id not in inventory_line_vals:
                                inventory_line_vals.update({location_id:''})

                            #For faster create inventory.
                            cr.execute("select sum(quantity) from stock_quant where company_id=%d and location_id=%d and product_id=%d"%(company_id, location_id,product_exist.id))
                            theoretical_qty = cr.fetchone()
                            theoretical_qty = theoretical_qty and theoretical_qty[0] or None
                            if theoretical_qty and inventory_option=='ADD':
                                product_qty += theoretical_qty
                            if theoretical_qty==None:
                                #if theoretical_qty==None:
                                theoretical_qty=0.0
                            if theoretical_qty!=product_qty:
                                if location_id not in location_id_inventory_dict:
                                    inventory_rec = inventory_obj.create({
                                                            'location_id':location_id,
                                                            'filter':'partial',
                                                            'name' : batch.name,
                                                            })
                                    location_id_inventory_dict.update({location_id:inventory_rec.id})
                                line = "(nextval('stock_inventory_line_id_seq'),%d,(now() at time zone 'UTC'),%d,(now() at time zone 'UTC'),%f,%d,%d,%d,%d,%d,%f),"%(uid,uid, product_qty,location_id, company_id, location_id_inventory_dict.get(location_id), product_exist.id,product_exist.uom_id.id,theoretical_qty)
                                inventory_line_vals[location_id] += line
                            #inventory_line_vals[location_id].append({'product_id':product_exist.id, 'product_uom_id': product_exist.uom_id.id,'product_qty':product_qty, 'location_id':location_id})
                if inventory_line_vals:
                    self.create_inventory(inventory_line_vals, location_id_inventory_dict)

                batch.write({'state':'imported'})
                cr.execute('RELEASE SAVEPOINT model_batch_save')
            except Exception as e:
                _logger.error(str(e))
                cr.execute('ROLLBACK TO SAVEPOINT model_batch_save')
                batch = self.browse(batch_id)
                batch.write({'state':'failed'})
                batch.message_post(body=str(e))
        return True
    @api.model
    def create_inventory(self, inventory_line_vals, location_id_inventory_dict):
        inventory_obj = self.env['stock.inventory']
        for location_id,inventory_vals in inventory_line_vals.items():
            inventory_id = location_id_inventory_dict.get(location_id)
            if not inventory_id:
                continue
            if inventory_vals[-1:]==',':
                inventory_vals = inventory_vals[:-1]
            if not inventory_vals:
                continue
            self._cr.execute("INSERT into stock_inventory_line(id,create_uid, create_date, write_uid, write_date, product_qty, location_id, company_id, inventory_id, product_id, product_uom_id, theoretical_qty) values%s"%inventory_vals)
            inventory_rec = inventory_obj.browse(inventory_id)
            inventory_rec.action_start()
            #inventory_rec.action_done() instead of this method, called below methods.
            inventory_rec.action_check()
            inventory_rec.write({'state': 'done'})
            inventory_rec.post_inventory()

        return True
    @api.model
    def get_create_xml_id(self,record, external_id):
        """ Return a valid xml_id for the record ``self``. """
        if external_id:
            #ir_model_data = self.sudo().env['ir.model.data']
            #data = ir_model_data.search([('model', '=', record._name), ('res_id', '=', record.id)])
            self._cr.execute("select id,module,name from ir_model_data where model='%s' and res_id=%d"%(record._name,record.id))
            data = self._cr.dictfetchone()
            if data:
                if data.get('module'):
                    existing_external_id =  '%s.%s' % (data.get('module'), data.get('name'))
                else:
                    existing_external_id =  data.get('name')
                if existing_external_id!=external_id:
                    self._cr.execute("delete from ir_model_data where id=%d"%(data.get('id')))
                    #data[0].unlink()
                else:
                    return existing_external_id
            external_ids = external_id.split('.')
            if len(external_ids)>1:
                name = '.'.join(external_ids[1:])
                module = external_ids[0]
            else:
                name = external_ids[0]
                module = ''
            uid = self._uid
            #TO Faster add record directly executed query.
            self._cr.execute("""insert into ir_model_data(id,create_uid,create_date, write_date, write_uid, name, module, model, res_id)
            values(nextval('ir_model_data_id_seq'),%d,(now() at time zone 'UTC'),(now() at time zone 'UTC'),%d, '%s','%s','%s',%d)"""%(uid,uid,name,module,record._name,record.id))
#             ir_model_data.create({
#                 'model': record._name,
#                 'res_id': record.id,
#                 'module': module,
#                 'name': name,
#             })
            return module+'.' + name

    @api.model
    def import_batch_product_data(self):
        batches = self.search([('state','=','pending')],limit=1,order='create_date')
        batches.action_import_product_data()
        return True