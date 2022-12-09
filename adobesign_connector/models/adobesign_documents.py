from odoo import api, fields, models, tools, _, Command
from odoo.exceptions import UserError, ValidationError
import base64
import re
import os
import requests
from odoo.tools import config

import logging
_logger = logging.getLogger(__name__)

class adobesignDocuments(models.Model):
    _name = 'adobesign.documents'

    name = fields.Char('Send To')
    email = fields.Char('Email')
    status = fields.Selection([
        ('not_sent','Not Sent'),
        ('sent', 'Sent'),
        ('in_progress','In Progress'),
        ('completed','Completed'),
        ('declined','Declined'),
        ],'adobesign Status',default='not sent')
    agreement_id = fields.Text('Envelope ID')
    move_id = fields.Many2one('account.move', string='Invoice')
    order_id = fields.Many2one('sale.order', string='Sale Order')
    completed_document = fields.Binary('Completed Document')
    completed_document_name = fields.Char('Document Name')
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)

    def update_status_cron(self):
        config = self.env['adobesign.config.settings'].sudo().search([('active','=', True)], limit=1)
        token = config.validate_token()
        documents = self.env['adobesign.documents'].sudo().search([('agreement_id', '!=', False),('status', '=', 'sent')])
        for rec in documents:
            agreementId = rec.agreement_id
            try:
                url = f"https://api.{config.as_region}.adobesign.com/api/rest/v6/agreements/{agreementId}"
                headers = {
                    'Authorization': 'Bearer ' + config.as_access_token,
                }
                payload = {}
                response = requests.get(url, headers=headers, data=payload)
                data = response.json()
                status = data.get('status')
                if status:
                    try:
                        if status == 'SIGNED':
                            rec.status = 'completed'
                        if status == 'OUT_FOR_SIGNATURE':
                            rec.status = 'in_progress'
                        if status == 'CANCELLED':
                            rec.status = 'declined'
                        
                        if status == 'SIGNED':
                            url = f"https://api.in1.adobesign.com/api/rest/v6/agreements/{agreementId}/combinedDocument/url"

                            payload={}
                            headers = {
                                'Authorization': 'Bearer ' + config.as_access_token,                            
                            }
                            response = requests.get(url, headers=headers, data=payload)
                            data = response.json()
                            url = data.get('url') 
                            req = requests.get(url)
                            encoded_string = base64.b64encode(req.content)
                            rec.completed_document = encoded_string
                            if rec.move_id:
                                rec.completed_document_name = 'Invoice.pdf' if not rec.move_id.name else rec.move_id.name + '.pdf'
                            if rec.order_id:
                                rec.completed_document_name = 'SaleOrder.pdf' if not rec.order_id.name else rec.order_id.name + '.pdf'
                            else:
                                rec.completed_document_name = 'SignedDocument.pdf'
                    except Exception as err:
                        raise UserError(_("Please check your adobesign configuration, Something went wrong :\n %s", tools.ustr(err)))
            except Exception as err:
                raise UserError(_("Please check your adobesign configuration, Something went wrong :\n %s", tools.ustr(err)))

        return True
        
    def update_status(self):
        config = self.env['adobesign.config.settings'].sudo().search([('active','=', True)], limit=1)
        token = config.validate_token()
        for rec in self:
            agreementId = rec.agreement_id
            try:            
                url = f"https://api.{config.as_region}.adobesign.com/api/rest/v6/agreements/{agreementId}"
                headers = {
                    'Authorization': 'Bearer ' + config.as_access_token,
                }
                payload = {}
                response = requests.get(url, headers=headers, data=payload)
                data = response.json()
                status = data.get('status')
                if status:
                    try:
                        if status == 'SIGNED':
                            rec.status = 'completed'
                        if status == 'OUT_FOR_SIGNATURE':
                            rec.status = 'in_progress'
                        if status == 'CANCELLED':
                            rec.status = 'declined'
                        
                        if status == 'SIGNED':
                            url = f"https://api.in1.adobesign.com/api/rest/v6/agreements/{agreementId}/combinedDocument/url"

                            payload={}
                            headers = {
                                'Authorization': 'Bearer ' + config.as_access_token,                            
                            }
                            response = requests.get(url, headers=headers, data=payload)
                            data = response.json()
                            url = data.get('url') 
                            req = requests.get(url)
                            encoded_string = base64.b64encode(req.content)
                            rec.completed_document = encoded_string
                            if rec.move_id:
                                rec.completed_document_name = 'Invoice.pdf' if not rec.move_id.name else rec.move_id.name + '.pdf'
                            if rec.order_id:
                                rec.completed_document_name = 'SaleOrder.pdf' if not rec.order_id.name else rec.order_id.name + '.pdf'
                            else:
                                rec.completed_document_name = 'SignedDocument.pdf'
                    except Exception as err:
                        raise UserError(_("Please check your adobesign configuration, Something went wrong :\n %s", tools.ustr(err)))
            except Exception as err:
                raise UserError(_("Please check your adobesign configuration, Something went wrong :\n %s", tools.ustr(err)))
        return True