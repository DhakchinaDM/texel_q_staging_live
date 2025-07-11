# -*- coding: utf-8 -*-
##############################################################################
{
    'name': 'Purchase Tender Management',
    'version': '17.12',
    'category': 'Purchases',
    'license': 'LGPL-3',
    'description': """A purchase tender management system assists users in efficiently handling procurement processes. 
    It allows users to record details of multiple vendors and the required products, along with the quantities needed
     to raise separate purchase requests. This enables the system to obtain quotes from various vendors, facilitating 
     the selection of the best price for generating a final purchase order to replenish our stock. Moreover, the system
      analyzes multiple requests for quotation (RFQ) to identify the most favorable option. Additionally, the system 
      generates detailed PDF reports, streamlining the confirmation of the tender management process.""",
    'summary': "Purchase tender management facilitates users in recording multiple vendors and the required product "
               "items along with demanded quantities to raise separate purchase requests. This allows for obtaining "
               "pricing from various vendors, with the best price being accepted and generated as a final purchase order"
               " to update our stock. Additionally, the system analyzes multiple requests for quotation (RFQ) to select "
               "the most favorable one. Tender PDF report generation further aids users in confirming the tender "
               "management process.",
    'author': 'AppsComp Widgets Pvt Ltd',
    'website': 'www.appscomp.com',
    "depends": ["base", "purchase", "stock", "purchase_request", "account", "mail", "portal", "utm",
                "purchase_requisition"],
    "application": True,
    "data": [
        'security/sh_purchase_tender_security.xml',
        'security/ir.model.access.csv',
        'report/apps_purchase_agreement_report.xml',
        'report/apps_report_analyze_quotation.xml',
        'data/sh_purchase_agreement_data.xml',
        'data/sh_purchase_tender_email_data.xml',
        'data/purchase_aggrement_type.xml',
        'views/sh_purchase_agreement_type_view.xml',
        'views/sh_purchase_agreement_view.xml',
        'views/apps_purchase_order_view.xml',
        'views/analyze_rfq_view.xml',
        'wizard/sh_update_qty_wizard_view.xml',
        'wizard/sh_purchase_order_wizard_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'price': '35',
    'currency': 'EUR',
    'installable': True,
    'active': True,

}
