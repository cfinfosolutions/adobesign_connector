# https://secure.na1.adobesign.com/public/static/oauthDoc.jsp#accessTokenRequest
# https://secure.na1.echosign.com/public/docs/restapi/v6#!/baseUris/getBaseUris

import requests
import base64
import sys
import subprocess

from os import path
from pytz import UTC
from datetime import date, datetime, time, timedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class adobesignConfigSettings(models.Model):
    _name = "adobesign.config.settings"
    _description = "adobesign Config Settings"

    name = fields.Char('Description')
    active = fields.Boolean(default=True)
    as_region = fields.Char(string='Region',help="only take the region portion, ie. na1, na2, eu1 etc")
    as_authorization_server = fields.Char(string="Base URL", compute="_compute_authorization_server", store=True)
    as_client_id = fields.Char('Client Id')
    as_client_secret = fields.Char('Client Secret')
    as_redirect_uri = fields.Char('Redirect URI(HTTPS)')
    as_access_token = fields.Text(string="Access Token")
    as_refresh_token = fields.Text(string="Refresh Token")
    state = fields.Selection([
        ('draft', 'Draft'), 
        ('authorized', 'Authorized'), 
        ('failed','Failed')
        ], default='draft',string='Status')
    as_authorization_url = fields.Text('Authorization URL')
    as_lastcall = fields.Datetime(string='Last Execution Date')
    as_authorization_approved = fields.Boolean(string="Is Authorization Approved", default=False)    
    as_authorization_code = fields.Text('Code')
    as_api_access_point = fields.Text('API Access Point')
    as_web_access_point = fields.Text('Web Access Point')

    def set_to_draft(self):
        for rec in self:
            rec.write({
                'as_authorization_approved': False,
                'as_authorization_url': False,
                'as_access_token': False,
                'as_lastcall': False,
                'state' : 'draft',
            })
    
    @api.depends('as_region')
    def _compute_authorization_server(self):
        for rec in self:
            if rec.as_region:
                rec.as_authorization_server = f'secure.{rec.as_region}.adobesign.com'
            else:
                rec.as_authorization_server = 'secure.adobesign.com'

    @api.constrains('active')
    def _check_is_selected(self):
        active = self.env['adobesign.config.settings'].search_count([('active', '=', True)])
        if active > 1:
            raise ValidationError("Active configuration is already here!")

    @api.model
    def default_get(self, fields):
        rec = super(adobesignConfigSettings, self).default_get(fields)
        IrConfig = self.env['ir.config_parameter'].sudo()
        redirect_uri = IrConfig.get_param('web.base.url') + "/adobesign/callback"
        rec.update(
            as_redirect_uri = redirect_uri
        )
        return rec

    def get_consent(self):
        for rec in self:
            authorization_server = rec.as_authorization_server
            response_type = "code"
            url_scopes = "signature%20impersonation"
            as_client_id = rec.as_client_id
            redirect_uri = rec.as_redirect_uri

            authorization_url = f"https://{authorization_server}/oauth/auth?response_type={response_type}&" \
                    f"scope={url_scopes}&client_id={as_client_id}&redirect_uri={redirect_uri}&state={str(rec.id)}"

            rec.write({
                'as_authorization_url' : authorization_url,
            })
            res = requests.get(authorization_url)
            return res
    
    def add_authorization_request(self):
        for rec in self:
            authorization_server = rec.as_authorization_server
            response_type = "code"
            url_scopes = "user_write:account+user_read:account+user_login:account+agreement_read:account+agreement_send:account+agreement_write:account"
            as_client_id = rec.as_client_id
            redirect_uri = rec.as_redirect_uri
            
            authorization_url = f"https://{authorization_server}/public/oauth/v2?redirect_uri={redirect_uri}&" \
                    f"response_type={response_type}&client_id={as_client_id}&scope={url_scopes}&" \
                    f"state={str(rec.id)}"

            rec.write({
                'as_authorization_url' : authorization_url,
            })

            return {
                'type': 'ir.actions.act_url',
                'url': authorization_url,
                'target': 'new',
                'target_type': 'public',
            }

    def run_authorize(self):
        for rec in self:
            response = rec.get_access_token()
            if response.status_code in (200, 201):
                data = response.json()
                rec.sudo().write({
                    'as_access_token' :  data.get('access_token'),
                    'as_refresh_token' : data.get('refresh_token'),
                    'as_api_access_point' : data.get('api_access_point'),
                    'as_web_access_point' : data.get('web_access_point'),
                    'as_lastcall' : fields.Datetime.now(),
                    'state' : 'authorized',
                })                
            else:
                err = response.json()
                raise ValidationError(_("Server replied with following exception:\n %s", tools.ustr(err.get('error_description'))))
        return True
    
    def get_access_token(self):
        for rec in self:            
            try:
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
                payload = {
                    'code': rec.as_authorization_code,
                    'client_id': rec.as_client_id,
                    'client_secret': rec.as_client_secret,
                    'redirect_uri': rec.as_redirect_uri,
                    'grant_type': 'authorization_code',
                }
                # Call the Adobe Sign API                
                url = f"https://api.{rec.as_region}.adobesign.com/oauth/v2/token"
                response = requests.post(url, headers=headers, data=payload, allow_redirects=False)
            except Exception:
                return False
            return response

    def refresh_token(self):
        for rec in self:
            try:
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
                payload = {
                    'refresh_token': rec.as_refresh_token,
                    'client_id': rec.as_client_id,
                    'client_secret': rec.as_client_secret,
                    'grant_type': 'refresh_token',
                }
                url = f"https://api.{rec.as_region}.adobesign.com/oauth/v2/refresh"
                response = requests.post(url, headers=headers, data=payload, allow_redirects=False)
                if response.status_code in (200, 201):                    
                    data = response.json()
                    rec.sudo().write({
                        'as_access_token' :  data.get('access_token'),
                        'as_lastcall' : fields.Datetime.now(),
                    }) 
                    return True
                else:
                    err = response.json()
                    raise ValidationError(_("Server replied with following exception:\n %s", tools.ustr(err.get('error_description'))))
            except Exception:
                return False

    def validate_token_cron(self):
        configs = self.env['adobesign.config.settings'].sudo().search([('active','=', True)])
        for config in configs:
            last_dt = config.as_lastcall if config.as_lastcall else fields.Datetime.now() - timedelta(hours=1)
            if last_dt:
                now_dt = fields.Datetime.now()
                if now_dt and not now_dt.tzinfo:
                    now_dt = now_dt.replace(tzinfo=UTC)        
                if last_dt and not last_dt.tzinfo:
                    last_dt = last_dt.replace(tzinfo=UTC)
                difference = (now_dt - last_dt).total_seconds() / 60
                minutes = round(difference, 2)
                if minutes > 45:
                    config.refresh_token()
                    _logger.warning('Created a new token at: %s', fields.Datetime.now())
        return True
    
    def validate_token(self):
        for rec in self:
            if rec.as_access_token:
                try:
                    url = "https://api.adobesign.com/api/rest/v6/baseUris"

                    payload={}
                    headers = {
                        'Authorization': 'Bearer ' + rec.as_access_token,
                    }
                    response = requests.get(url, headers=headers, data=payload)
                    if response.status_code in (200, 201):
                        return True
                    else:
                        rec.refresh_token()
                except Exception:
                    pass
            else:
                raise UserError(_("adobesign access token not detected; contact administrator."))
        return True