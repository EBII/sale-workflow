# coding: utf-8
# © 2015 Akretion, Valentin CHEMIERE <valentin.chemiere@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, api, models


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name', store=True, index=True)
    option_qty = fields.Integer(
        string="Option Qty", oldname='default_qty',
        help="This is the default quantity set to the sale line option ")
    opt_max_qty = fields.Integer(
        string="Max Qty Opt", oldname='max_qty',
        help="High limit authorised in the sale line option")

    @api.multi
    @api.depends('product_id', 'product_id.product_tmpl_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.product_id.name

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        new_domain = self._filter_bom_lines_for_sale_line_option(args)
        res = super(MrpBomLine, self).name_search(
            name=name, args=new_domain, operator=operator, limit=limit)
        return res

    def search(self, domain, offset=0, limit=None, order=None, count=False):
        new_domain = self._filter_bom_lines_for_sale_line_option(domain)
        return super(MrpBomLine, self).search(
            new_domain, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def _filter_bom_lines_for_sale_line_option(self, domain):
        product = self.env.context.get('filter_bom_with_product')
        if isinstance(product, int):
            product = self.env['product.product'].browse(product)
        if product:
            new_domain = [
                '|',
                '&',
                ('bom_id.product_tmpl_id', '=', product.product_tmpl_id.id),
                ('bom_id.product_id', '=', False),
                ('bom_id.product_id', '=', product.id)]
            domain += new_domain
        return domain


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    @api.model
    def _skip_bom_line(self, line, product):
        res = super(MrpBom, self)._skip_bom_line(line, product)
        prod_id = self.env.context['production_id']
        prod = self.env['mrp.production'].browse(prod_id)
        bom_lines = [option.bom_line_id
                     for option in prod.lot_id.option_ids]
        if line in bom_lines:
            return res
        else:
            return True

    @api.model
    def _prepare_conssumed_line(self, bom_line, quantity, product_uos_qty):
        vals = super(MrpBom, self)._prepare_conssumed_line(
            bom_line, quantity, product_uos_qty)
        prod = self.env['mrp.production'].browse(
            self.env.context['production_id'])
        for option in prod.lot_id.option_ids:
            if option.bom_line_id == bom_line:
                vals['product_qty'] = vals['product_qty'] * option.qty
        return vals