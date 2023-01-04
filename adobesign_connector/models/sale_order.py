import re
import os
import base64
import requests
import json

from odoo.tools import config
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    adobesign_documents_line_ids = fields.One2many('adobesign.documents','order_id','adobesign Documents')

    def get_report_file(self):
        file = None
        for rec in self:            
            report = self.env.ref('sale.action_report_saleorder')._render_qweb_pdf([rec.id])
            if report:
                datas =base64.b64encode(report[0])
                attachment = self.env['ir.attachment'].create({
                    'name': "SaleOrder" if not rec.name else rec.name,
                    'type': 'binary',
                    'datas': datas,
                    'store_fname': "SaleOrder" + '.pdf' if not rec.name else rec.name + '.pdf',
                    'res_model': self._name,
                    'res_id': rec.id,
                    'mimetype': 'application/x-pdf'
                })
                full_path = attachment._full_path(attachment.store_fname)
                with open(full_path, "rb") as data:
                    file = data.read()
                attachment.unlink()
            else:
                raise UserError(_('Sale Report not found.'))
        return file
        
    def create_transient_documents(self, region, token, file_name, file):
        files=[
            ('File',(file_name + '.pdf', file, 'application/pdf'))
        ]
        try:            
            url = f"https://api.{region}.adobesign.com/api/rest/v6/transientDocuments"
            payload={}
            headers = {
                'Authorization': 'Bearer ' + token,
            }
            response = requests.post(url, headers=headers, data=payload, files=files)
            if response.status_code in (200, 201):
                return response
            else:
                raise ValidationError("Failure to create a transitory document, please check the access token.")
        except Exception:
            pass
    
    def create_agreements(self, region, token, transientDocumentId, email, recId):
        try:
            url = f"https://api.{region}.adobesign.com/api/rest/v6/agreements"
            payload = json.dumps({
                "fileInfos": [
                    {
                        "transientDocumentId": transientDocumentId,
                    }
                ],
                "name": "API Send Transient Test Agreement",
                "participantSetsInfo": [
                    {
                        "memberInfos": [
                            {
                                "email": email,
                            }
                        ],
                        "order": 1,
                        "role": "SIGNER"
                    }
                ],
                "signatureType": "ESIGN",
                "externalId": {
                    "id": recId
                },
                "state": "IN_PROCESS"
            })

            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token,
            }
            response = requests.post(url, headers=headers, data=payload)            
            if response.status_code in (200, 201):
                return response
            else:
                raise ValidationError("Failure to create a agreement document, please check the access token.")
        except Exception:
            pass


    def get_signature(self):
        adobesign_documents_obj = self.env['adobesign.documents']
        config = self.env['adobesign.config.settings'].sudo().search([('active','=', True)], limit=1)
        region = config.as_region
        token = config.validate_token()
        for rec in self:
            if not rec.partner_id.email:
                raise ValidationError("Partner email not found.")

            file = self.get_report_file()
            if not file:
                raise ValidationError("Report not found.")
            
            if config.as_access_token:
                transientDocument = self.create_transient_documents(region, config.as_access_token, rec.name, file)
                data = transientDocument.json()
                transientDocumentId = data.get('transientDocumentId')
                if transientDocumentId:
                    agreement = self.create_agreements(region, config.as_access_token, transientDocumentId, rec.partner_id.email, rec.id)
                    data = agreement.json()
                    agreement_id = data.get('id')
                    if agreement_id:
                        _logger.warning(agreement_id)
                        adobesign_documents_obj.create({
                            'name' : rec.partner_id.name,
                            'email' : rec.partner_id.email,
                            'status' : 'sent',
                            'agreement_id' : agreement_id,
                            'order_id' : rec.id,
                        })
            else:
                raise ValidationError("Access Token not found.")
            
        

    def _full_path(self, path):
        path = re.sub('[.]', '', path)
        path = path.strip('/\\')
        return os.path.join(self._filestore(), path)

    def _filestore(self):
        return config.filestore(self._cr.dbname)
