# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Inventory Ageing Report in Excel',
    'version': '17.1',
    'category': 'Warehouse',
    'summary': 'This module will print excel report of Stock Ageing.',
    'author': 'AppsComp Widgets Pvt Ltd',
    'license': 'LGPL-3',
    "live_test_url": "https://youtu.be/qfn_4u_uwF4",
    'description': """
            Inventory ageing reports tell you the number of days an item has been sitting in inventory based on the receipt date. Having access to this kind of information allows you to make informed decisions when it comes to what and how many products to purchase.""",
    'depends': ['base', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/inventory_report_view.xml',
        'wizard/current_stock_report.xml',
    ],
    'demo': [
    ],
    'css': [],
    'installable': True,
    'auto_install': False,
}
