# -*- coding: utf-8 -*-
###############################################################################
#
#   Module for Odoo
#   Copyright (C) 2015 Akretion (http://www.akretion.com).
#   @author Valentin CHEMIERE <valentin.chemiere@akretion.com>
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


from openerp.osv import orm


class StockMove(orm.Model):
    _inherit = 'stock.move'

    #Complicated code that explode the prodlot number
    #base function are really ugly, hard to inherit
    def _action_explode(self, cr, uid, move, context=None):
        """ only acts on sold products with phantom bom
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['lot_base_name'] = move.restrict_lot_id.name
        ctx['lot_index'] = 1
        ctx['explode_lot'] = True

        return super(StockMove, self)._action_explode(
            cr, uid, move, context=ctx)

    def _prepare_explode_move(self, cr, uid, move, line, context=None):
        product_obj = self.pool['product.product']
        lot_obj = self.pool['stock.production.lot']
        if context is None:
            context = {}
        res = super(StockMove, self).\
            _prepare_explode_move(cr, uid, move, line, context=context)
        if context.get('explode_lot'):
            if move.product_id.sale_prodlot_generation:
                product = product_obj.browse(
                    cr, uid, line['product_id'], context=context)
                if product.sale_prodlot_generation:
                    lot_vals = self._prepare_lot_for_move(
                        cr, uid, line['product_id'], move,
                        context['lot_index'], context=context)
                    res['restrict_lot_id'] = lot_obj.create(
                        cr, uid, lot_vals, context=context)
                    context['lot_index'] += 1
        return res

    def _prepare_lot_for_move(
            self, cr, uid, product_id, move, lot_index, context=None):
        lot_number = "%s-%03d" % (
            move.restrict_lot_id.name, lot_index)
        return {
            'name': lot_number,
            'product_id': product_id,
            'company_id': move.company_id.id,
        }

    def create_chained_picking(self, cr, uid, moves, context=None):
        # It should be removed, replaced by route mechanism ?
        new_moves = super(StockMove, self).create_chained_picking(
            cr, uid, moves, context=context)
        for new_move in new_moves:
            if new_move.move_dest_id.restrict_lot_id:
                new_move.write({
                    'restrict_lot_id': new_move.move_dest_id.restrict_lot_id.id,
                })
        return new_moves
