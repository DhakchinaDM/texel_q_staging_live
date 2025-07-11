{
    'name': 'OnHand Screen',
    'version': '17.0.1.0.4',
    'sequence': 1,
    'license': 'LGPL-3',
    'depends': ["base", "web",'stock'],
    'module_type': '',
    'data': [
        'views/xml_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2/select2.js',
            'onhand_product_js/static/src/js/product.js',
            'onhand_product_js/static/src/xml/product.xml',
            'onhand_product_js/static/src/css/product.css',
        ],
    },
    'application': True,
}

