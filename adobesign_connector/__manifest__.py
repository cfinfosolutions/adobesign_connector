# -*- coding: utf-8 -*-
#################################################################################
# Author      : CFIS (<https://www.cfis.store/>)
# Copyright(c): 2017-Present CFIS.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://www.cfis.store/>
#################################################################################

{
    "name": "Adobe Sign | Odoo Adobe Sign Integration | Odoo Adobe Sign Connector | AdobeSign",
    "summary": """
        This module allows the odoo users Integration with Adobe Sign. We will send emails to users asking them to 
        sign the document (Invoice and Sale Order) after setting up the adobesign email. Use the Adobe Sign to retrieve the document.
        """,
    "version": "13.0.1",
    "description": """
        This module allows the odoo users Integration with Adobe Sign. We will send emails to users asking them to 
        sign the document (Invoice and Sale Order) after setting up the Adobe Sign email. Use the Adobe Sign to retrieve the document.
    """,    
    "author": "CFIS",
    "maintainer": "CFIS",
    "license" :  "Other proprietary",
    "website": "https://www.cfis.store",
    "images": ["images/adobesign_connector.png"],
    "category": "Extra Tools",
    "depends": [
        "web",
        "sale_management",
        "account"
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/adobesign_documents_views.xml",
        "views/adobesign_config_settings.xml",
    ],
    "assets": {
        
    },
    "installable": True,
    "application": True,
    "price"                 :  175.00,
    "currency"              :  "EUR",
    "pre_init_hook"         :  "pre_init_check",
}
