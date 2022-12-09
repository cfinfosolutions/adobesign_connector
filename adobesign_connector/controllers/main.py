from odoo import http
from odoo.http import request, route

class adobesignConnector(http.Controller):
    @http.route(['/adobesign/callback'], type='http', auth="public", website=True)
    def adobesign_callback(self, **kwargs):
        if kwargs and 'code' in kwargs and 'state' in kwargs:
            rec_id = request.env['adobesign.config.settings'].sudo().browse(int(kwargs['state']))
            rec_id.sudo().write({
                'as_authorization_code' : kwargs['code'],
                'as_authorization_approved' : True,
            })
            rec_id.sudo().run_authorize()
            return 'Connection Successful.Please reload the previous page and try it again.'
        else:
            return 'Connection Unsuccessful.Please check connection details try it again.'