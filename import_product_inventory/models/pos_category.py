# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _

class PosCategory(models.Model):
    _inherit = "pos.category"
    
    complete_categ_name = fields.Char('Complete Name', compute='_compute_complete_categ_name',store=True)
    
    @api.depends('name', 'parent_id.complete_categ_name')
    def _compute_complete_categ_name(self):
        for category in self:
            if category.parent_id:
                category.complete_categ_name = '%s / %s' % (category.parent_id.complete_categ_name, category.name)
            else:
                category.complete_categ_name = category.name