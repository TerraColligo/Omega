# -*- coding: utf-8 -*-
from odoo import models,api,fields
from odoo.exceptions import Warning
#import itertools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from odoo.tools.mimetypes import guess_mimetype
import os
import json
import base64
    
import logging
_logger = logging.getLogger(__name__)
try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

try:
    import odf_ods_reader
except ImportError:
    odf_ods_reader = None

FILE_TYPE_DICT = {
    'text/csv': ('csv', True, None),
    'application/vnd.ms-excel': ('xls', xlrd, 'xlrd'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('xlsx', xlsx, 'xlrd >= 0.8'),
    'application/vnd.oasis.opendocument.spreadsheet': ('ods', odf_ods_reader, 'odfpy')
}
EXTENSIONS = {
    '.' + ext: handler
    for mime, (ext, handler, req) in FILE_TYPE_DICT.items()
}
class import_product_from_file(models.TransientModel):
    _name ='import.product.from.file'
    
    import_file = fields.Binary("Import Excel File",required=False)
    file_name = fields.Char("Filename")
    inventory_option = fields.Selection([('ADD','ADD'),('SET','SET')],string="Inventory Option",
                                        help="""
                                        If ADD, system will add quantity in existing Quantity for particualar product.
                                        i.e. Product Apple have 10 Quantity in Warehouse A and user try to import inventory with option ADD and Product Apple with quantity=100 in file,
                                             system will add 100 quantity in existing Quantity, so after import, inventory of Apple product is 110.
                                        
                                        If SET, system will set whatever quantity given in file for particular product. 
                                        i.e. Product Apple have 10 Quantity in Warehouse A and user try to import inventory with option SET and Product Apple with quantity=100 in file,
                                             system will set 100 quantity for product Apple, so after import, inventory of Apple product is 100.
                                        """)
    
    @api.multi
    def import_product_and_inventory_from_file(self):
        self.ensure_one()
        if not self.import_file:
            raise Warning("Please select the file first.") 
        p, ext = os.path.splitext(self.file_name)
        if ext[1:] not in ['xls','xlsx']:
            raise Warning(_("Unsupported file format \"{}\", import only supports XLS, XLSX").format(self.file_name))
            
        # guess mimetype from file content
        options = {u'datetime_format': u'', u'date_format': u'', u'keep_matches': False, u'encoding': u'utf-8', u'fields': [], u'quoting': u'"', u'headers': True, u'separator': u',', u'float_thousand_separator': u',', u'float_decimal_separator': u'.', u'advanced': False}
        import_file = base64.b64decode(self.import_file)
        mimetype = guess_mimetype(import_file)
        (file_extension, handler, req) = FILE_TYPE_DICT.get(mimetype, (None, None, None))
        rows = []
        result = []
        if handler:
            result = getattr(self, '_read_' + file_extension)(options,import_file)
        if not result and self.file_name:
            p, ext = os.path.splitext(self.file_name)
            if ext in EXTENSIONS:
                result = getattr(self, '_read_' + ext[1:])(options,import_file)
        if not result and req:
            raise Warning(_("Unable to load \"{extension}\" file: requires Python module \"{modname}\"").format(extension=file_extension, modname=req))
        
        import_batch_obj = self.env['product.import.batch']
        for sheet_name,rows in result:
            if rows:
                index = 1
                for split_rows in self.split_rows(rows,500):
                    import_batch_obj.create({'inventory_option':self.inventory_option,'name':sheet_name+' '+str(index),'sheet_name':sheet_name+' '+str(index),'state':'pending','data':json.dumps(split_rows)})
                    index += 1
        if result:
            self._cr.commit()
            raise Warning('Please wait a moment, system will import product in batch.')      
            #return {'type': 'ir.actions.act_window_close'}
        raise ValueError(_("Unsupported file format \"{}\", import only supports XLS and XLSX").format(self.file_name))
    
    def split_rows(self, array, size):
        arrs = []
        while len(array) > size:
            pice = array[:size]
            arrs.append(pice)
            array = array[size:]
        arrs.append(array)
        
        return arrs
    
    @api.multi
    def _read_xls(self, options,import_file):
        """ Read file content, using xlrd lib """
        book = xlrd.open_workbook(file_contents=import_file)
        return self._read_xls_book(book)
    
    def _read_xls_book(self, book):
        result = []
        for sheet in book.sheets():
            sheet_name = sheet.name
            header = []
            records = []
            for row in map(sheet.row, range(sheet.nrows)):
                values = []
                for cell in row:
                    if cell.ctype is xlrd.XL_CELL_NUMBER:
                        is_float = cell.value % 1 != 0.0
                        values.append(
                            str(cell.value)
                            if is_float else str(int(cell.value))
                        )
                    elif cell.ctype is xlrd.XL_CELL_DATE:
                        is_datetime = cell.value % 1 != 0.0
                        # emulate xldate_as_datetime for pre-0.9.3
                        dt = datetime(*xlrd.xldate.xldate_as_tuple(cell.value, book.datemode))
                        values.append(
                            dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            if is_datetime
                            else dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
                        )
                    elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                        values.append(u'True' if cell.value else u'False')
                    elif cell.ctype is xlrd.XL_CELL_ERROR:
                        raise ValueError(
                            _("Error cell found while reading XLS/XLSX file: %s") %
                            xlrd.error_text_from_code.get(
                                cell.value, "unknown error code %s" % cell.value)
                        )
                    else:
                        values.append(cell.value)
                if any(x for x in values if x.strip()):
                    if not header:
                        header = values
                        #header = [x.lower() for x in header]
                        continue
                    dictionary = dict(zip(header, values))
                    if '' in dictionary:
                        dictionary.pop('')
                        dict_val = list(set(dictionary.values()))
                        if not dictionary or (len(dict_val)==1 and not dict_val[0]):
                            continue    
                    records.append(dictionary)
            result.append((sheet_name, records))         
        return result
    
    # use the same method for xlsx and xls files
    _read_xlsx = _read_xls
    