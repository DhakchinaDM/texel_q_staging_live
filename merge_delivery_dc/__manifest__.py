{
    'name': 'Merge Delivery Challan',
    'version': '17.0.0.4',
    'category': 'Warehouses',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'description': """ Delivery Challan""",
    'summary': 'Delivery Challan',
    'author': 'AppsComp Widgets Pvt Ltd',
    'website': 'www.appscomp.com',
    'depends': ['stock', 'delivery_challan'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/stock_operation_type.xml',
        'views/merge_picking_order.xml',
        # 'views/res_config_view.xml',
        # 'views/job_work_type.xml',
    ],
    'installable': True,
    'currency': 'EUR',
    'active': True,

}
