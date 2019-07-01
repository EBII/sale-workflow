# coding: utf-8
# © 2015 Akretion, Valentin CHEMIERE <valentin.chemiere@akretion.com>
# © 2017 David BEAL @ Akretion
# © 2019 Mourad EL HADJ MIMOUNE @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, api, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    base_price_unit = fields.Float(string='Base Price Unit')
    pricelist_id = fields.Many2one(
        related="order_id.pricelist_id", readonly=True)
    option_ids = fields.One2many(
        comodel_name='sale.order.line.option',
        inverse_name='sale_line_id', string='Options', copy=True,
        help="Options can be defined with product options")
    display_option = fields.Boolean(
        help="Technical: allow conditional options field display")

    @api.model
    def _add_missing_fields_get_onchange_fields(self):
        onchange_fields = super(SaleOrderLine, self)._add_missing_fields_get_onchange_fields()
        onchange_fields.append('option_ids')
        return onchange_fields

    @api.model
    def create(self, vals):
        if 'product_id' in vals:
            if self.env.context.get('install_mode'):
                # onchange are not played in install mode
                vals = self.play_onchanges(
                    vals, ['product_id', 'product_uom_qty'])
        return super(SaleOrderLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'option_ids' in vals:
            option_ids_val = vals['option_ids']
            # to fix issue of nesteed many2one we replace [5], [4] option of
            # one2many fileds by [6] option (same as : https://github.com/odoo/odoo/issues/17618)
            if option_ids_val and option_ids_val[0][0] == 5 and\
                    len(option_ids_val) > 1 and option_ids_val[1][0] == 4:
                opt_keep_ids = []
                for opt_v in option_ids_val[1:]:
                    if opt_v[0] == 4:
                        opt_keep_ids.append(opt_v[1])
                vals['option_ids'] = [(6, 0, opt_keep_ids)]
        return super(SaleOrderLine, self).write(vals)

    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            self.option_ids = False
            values = self._set_product(self.product_id, self.price_unit)
            for field in values:
                self[field] = values[field]
        return res

    def _set_product(self, product, price_unit):
        """ Shared code between onchange and create/write methods """
        implied = {}
        implied['display_option'], implied['option_ids'] = \
            self._set_option_lines(product)
        implied['base_price_unit'] = price_unit
        return implied

    @api.model
    def _set_option_lines(self, product):
        lines = []
        display_option = False
        pdtoptline = None
        prod_opt_lines = self.env['product.option.line'].with_context(
            prodopt_parent_with_product=product).search([])
        for pdtoptline in prod_opt_lines:
            if pdtoptline.opt_default_qty:  # TODO: changer pour pdtoptline.is_option?
                vals = {'product_option_line_id': pdtoptline.id,
                        'product_id': pdtoptline.product_id.id,
                        'qty': pdtoptline.opt_default_qty}
                lines.append((0, 0, vals))  # create
        if pdtoptline:
            display_option = True
        return (display_option, lines)

    @api.onchange('option_ids', 'base_price_unit')
    def _onchange_option(self):
        final_options_price = 0
        for option in self.option_ids:
            final_options_price += option.line_price
            self.price_unit = final_options_price + self.base_price_unit


class SaleOrderLineOption(models.Model):
    _name = 'sale.order.line.option'

    sale_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        required=True,
        ondelete='cascade')
    product_option_line_id = fields.Many2one(
        comodel_name='product.option.line', string='Product Option Line', ondelete="set null")
    product_ids = fields.Many2many(
        comodel_name='product.product', compute='_compute_opt_products')
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product', required=True)
    qty = fields.Integer(default=lambda x: x.default_qty)
    min_qty = fields.Integer(
        related='product_option_line_id.opt_min_qty', readonly=True)
    default_qty = fields.Integer(
        related='product_option_line_id.opt_default_qty', readonly=True)
    max_qty = fields.Integer(
        related='product_option_line_id.opt_max_qty', readonly=True)
    invalid_qty = fields.Boolean(
        compute='_compute_invalid_qty', store=True,
        help="Can be used to prevent confirmed sale order")
    line_price = fields.Float(compute='_compute_price', store=True)

    _sql_constraints = [
        ('option_unique_per_line',
         'unique(sale_line_id, product_id)',
         'Option must be unique per Sale line. Check option lines'),
    ]

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderLineOption, self).default_get(fields)
        line_product_id = self.env.context.get('line_product_id')
        if line_product_id:
            prod_opt_lines = self.env['product.option.line'].with_context(
                prodopt_parent_with_product=line_product_id).search([])
            res['product_ids'] = [x.product_id.id for x in prod_opt_lines]
        return res

    @api.model
    def create(self, vals):
        res = super(SaleOrderLineOption, self).create(vals)
        res.sale_line_id._onchange_option()
        return res

    @api.onchange('product_id')
    def _onchange_product(self):
        """ we need to store product_option_line_id to compute option price """
        ctx = {'prodopt_parent_with_product': self.env.context.get(
            line_product_id)}
        prod_opt_line = self.env['product.option.line'].with_context(ctx).search([
            ('product_id', '=', self.product_id.id)], limit=1)
        self.product_option_line_id = prod_opt_line and prod_opt_line.id

    def _compute_opt_products(self):
        """ required to set available options """
        prd_ids = [x.product_id.id
                   for x in self[0].product_option_line_id.\
                           parent_product_id.product_option_line_ids]
        for rec in self:
            rec.product_ids = prd_ids

    def _get_prod_opt_line_price(self):
        self.ensure_one()
        ctx = {'uom': self.product_option_line_id.product_uom_id.id}
        if self.sale_line_id.order_id.date_order:
            ctx['date'] = self.sale_line_id.order_id.date_order
        pricelist = self.sale_line_id.pricelist_id.with_context(ctx)
        price = pricelist.price_get(
            self.product_id.id,
            self.qty,
            self.sale_line_id.order_id.partner_id.id)
        return price[pricelist.id] * self.qty

    @api.depends('qty', 'product_id')
    def _compute_price(self):
        for record in self:
            if record.product_id and record.sale_line_id.pricelist_id:
                record.line_price = record._get_prod_opt_line_price()
            else:
                record.line_price = 0

    def _is_quantity_valid(self, record):
        """Ensure product_qty <= qty <= max_qty."""
        if not record.product_option_line_id:
            return True
        if record.qty < record.product_option_line_id.opt_min_qty:
            return False
        if record.qty > record.product_option_line_id.opt_max_qty:
            return False
        return True

    @api.depends('qty')
    def _compute_invalid_qty(self):
        for record in self:
            record.invalid_qty = not self._is_quantity_valid(record)

    @api.onchange('qty')
    def onchange_qty(self):
        for record in self:
            if not self._is_quantity_valid(record):
                max_val = record.qty
                record.qty = record.max_qty
                return {'warning': {
                    'title': _('Error on quantity'),
                    'message': _(
                        "Maximal quantity of this option is %(max)s.\n"
                        "You encoded %(qty)s.\n"
                        "Quantity is set max value") % {
                            'qty': max_val,
                            'max': record.max_qty}
                    }
                }
