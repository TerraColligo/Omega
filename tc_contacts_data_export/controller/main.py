# -*- coding: utf-8 -*-
from odoo import http

import base64
from odoo.http import request,content_disposition
from odoo.addons.web.controllers.main import serialize_exception

class DownloadFile(http.Controller):
    
    @http.route('/web/binary/savefile_custom', type='http', auth="public")
    @serialize_exception
    def saveas(self, model, field, id=None, filename_field=None,file_name=None, **kw):
        """ Download link for files stored as binary fields.

        If the ``id`` parameter is omitted, fetches the default value for the
        binary field (via ``default_get``), otherwise fetches the field for
        that precise record.

        :param str model: name of the model to fetch the binary from
        :param str field: binary field
        :param str id: id of the record from which to fetch the binary
        :param str filename_field: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        Model = request.env[model]
        fields = [field]
        if filename_field:
            fields.append(filename_field)
        if id:
            id = int(id)
            res = Model.browse(id).read(fields)[0]
        else:
            res = Model.default_get(fields)
        filecontent = base64.b64decode(res.get(field) or '')
        content_type = kw.get('content_type', 'application/octet-stream')
        if not filecontent:
            return request.not_found()
        else:
            filename = '%s_%s' % (model.replace('.', '_'), id)
            if file_name:
                filename = file_name 
            elif filename_field:
                filename = res.get(filename_field, '') or filename
            
            if id and kw.get("delete_document",False):
                Model.sudo().browse(id).write({field:False})
            return request.make_response(filecontent,
                [('Content-Type', content_type),
                 ('Content-Disposition', content_disposition(filename))])
    