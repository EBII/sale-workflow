# -*- coding: utf-8 -*-
# Copyright 2014-2016 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2016 Sodexis (http://sodexis.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Link rental service -> rented HW product
    rented_product_ids = fields.Many2many(
        comodel_name='product.product',
        relation='rental_product_rel',
        column1='rental_product_id',
        column2='rented_product_id',
        string='Related Rented Products',
        domain=[('type', 'in', ('product', 'consu'))])
    # Link rented HW product -> rental service
    rental_service_ids = fields.Many2many(
        comodel_name='product.product',
        relation='rental_product_rel',
        column1='rented_product_id',
        column2='rental_product_id',
        string='Related Rental Services')

    @api.constrains('rented_product_ids', 'must_have_dates', 'type', 'uom_id')
    def _check_rental(self):
        for product in self:
            if product.rented_product_ids and product.type != 'service':
                raise ValidationError(_(
                    "The rental product '%s' must be of type 'Service'.")
                    % product.name)
            if product.rented_product_ids and not product.must_have_dates:
                raise ValidationError(_(
                    "The rental product '%s' must have the option "
                    "'Must Have Start and End Dates' checked.")
                    % product.name)
            # In the future, we would like to support all time UoMs
            # but it is more complex and requires additionnal developments
            time_uom_categ = product.env.ref('product.uom_categ_wtime')
            if product.rented_product_ids and product.uom_id.category_id != time_uom_categ:
                raise ValidationError(_(
                    "The category of the unit of measure of the rental product "
                    "'%s' must be 'Working time'.") % product.name)

    @api.multi
    def _need_procurement(self):
        # Missing self.ensure_one() in the native code !
        res = super(ProductProduct, self)._need_procurement()
        if not res:
            for product in self:
                if product.type == 'service' and product.rented_product_ids:
                    return True
        # TODO find a replacement for soline.rental_type == 'new_rental')
        return res
