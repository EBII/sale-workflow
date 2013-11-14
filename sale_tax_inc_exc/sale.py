# -*- coding: utf-8 -*-
###############################################################################
#
#   Module for OpenERP 
#   Copyright (C) 2011-2013 Akretion (http://www.akretion.com).
#   @author Sébastien BEAU <sebastien.beau@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp.osv import orm, fields
import decimal_precision as dp
from tools.translate import _
from invoice_sale import InvoiceSale, InvoiceSaleLine

class sale_order(InvoiceSale):
    _inherit = "sale.order"

    _columns = {
        'tax_inc' : fields.boolean('Tax Inc', help="Tic the box if you want to use unit price in taxe include"),
    }

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        result = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context=context)
        result['tax_inc'] = order.tax_inc
        return result

class sale_order_line(InvoiceSaleLine):
    _inherit = "sale.order.line"

