{
    'name': 'POS Custom UI',
    'version': '1.0.0',
    'category': 'Point of Sale',
    'summary': 'Expose all-language product names for POS and Self Order frontends',
    'depends': ['point_of_sale', 'pos_self_order', 'product'],
    'data': [],
    'assets': {
        'pos_self_order.assets': [
            'pos_custom_ui/static/src/app/pages/product_list_page/product_list_page.js',
            'pos_custom_ui/static/src/app/pages/product_list_page/product_list_page.xml',
            'pos_custom_ui/static/src/app/pages/product_list_page/product_list_page.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
