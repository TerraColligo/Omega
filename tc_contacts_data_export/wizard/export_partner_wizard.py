# -*- coding: utf-8 -*-

from odoo import models,api,fields, _
from datetime import datetime
import uuid
import io
from odoo.tools.misc import xlwt
import base64


class export_partner_with_file(models.TransientModel):
    _name ='export.partner.with.file'

    file_data = fields.Binary("File Data")

    @api.multi
    def export_partners(self):
        filename = 'contacts_%s.xls'%(datetime.today().strftime("%Y_%m_%d_%H_%M_%S"))
        workbook = xlwt.Workbook()
        bold = xlwt.easyxf("font: bold on;")

        partners = self.env['res.partner'].sudo().search(['|', ('active', '=', False), ('active', '=', True)])

        worksheet = workbook.add_sheet('Contacts')

        headers = ['id','Name','Company Name','Salesperson','Pricelist','Customer Payment Terms', 'Supplier Payment Terms', 'Sales Agent Name', 'Sales Commission Percentage']

        partner_xml_ids = dict(self.__ensure_xml_id_custom(partners))

        for i,header in enumerate(headers):
            worksheet.write(0, i, header, bold)
            worksheet.col(i).width = 8000 # around 220 pixels

        def splittor(rs):
            for idx in range(0, len(rs), 1000):
                sub = rs[idx:idx+1000]
                for rec in sub:
                    yield rec
                rs.invalidate_cache(ids=sub.ids)
        row_index = 1
        for partner in splittor(partners):
            i=0
            worksheet.write(row_index, i, partner_xml_ids.get(partner.id))
            i +=1
            worksheet.write(row_index, i, partner.name)
            i +=1
            worksheet.write(row_index, i, partner.company_id.name or '')
            i +=1
            worksheet.write(row_index, i, partner.user_id.name or '')
            i +=1
            worksheet.write(row_index, i, partner.property_product_pricelist.name or '')
            i +=1
            worksheet.write(row_index, i, partner.property_payment_term_id.name or '')
            i +=1
            worksheet.write(row_index, i, partner.property_supplier_payment_term_id.name or '')
            i +=1
            worksheet.write(row_index, i, partner.sale_agent_id.name or '')
            i +=1
            worksheet.write(row_index, i, partner.commission_per or '0')
            row_index += 1

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

        return (
            (record.id, to_xid(record.id))
            for record in records
        )
