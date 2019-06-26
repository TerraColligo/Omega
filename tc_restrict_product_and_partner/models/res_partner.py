# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Partner(models.Model):
    _inherit = "res.partner"

    mobile = fields.Char(string="Mobile", required=True)

    @api.model
    def create(self, vals):
        if not vals.get('mobile'):
            raise UserError(_("Mobile Number is required for partner."))
        return super(Partner, self).create(vals)


class Users(models.Model):
    _inherit = "res.users"

    mobile = fields.Char(related='partner_id.mobile', inherited=True, readonly=False)


class Company(models.Model):
    _inherit = "res.company"

    mobile = fields.Char(related='partner_id.mobile', store=True, readonly=False)

    @api.model
    def create(self, vals):
        context = dict(self.env.context)
        context.update({'default_mobile': vals.get('mobile')})
        partner = self.env['res.partner'].create({
            'name': vals['name'],
            'is_company': True,
            'image': vals.get('logo'),
            'customer': False,
            'email': vals.get('email'),
            'phone': vals.get('phone'),
            'website': vals.get('website'),
            'vat': vals.get('vat'),
            'mobile': vals.get('mobile'),
        })
        vals['partner_id'] = partner.id
        res = super(Company, self).create(vals)
        res.partner_id.mobile = res.mobile
        return res
