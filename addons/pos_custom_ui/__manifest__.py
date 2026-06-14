{
    'name': 'POS Custom UI',
    'version': '1.0.0',
    'category': 'Point of Sale',
    'summary': 'Expose all-language product names for POS and Self Order frontends',
    'depends': ['point_of_sale', 'pos_self_order', 'product'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_custom_ui/static/src/app/services/pos_store.js',
            'pos_custom_ui/static/src/app/components/category_selector/category_selector.js',
            'pos_custom_ui/static/src/app/components/category_selector/category_selector.scss',
            'pos_custom_ui/static/src/app/screens/product_screen/order_summary/order_summary.js',
            'pos_custom_ui/static/src/app/screens/product_screen/product_screen.js',
            'pos_custom_ui/static/src/app/screens/product_screen/product_screen.xml',
            'pos_custom_ui/static/src/app/screens/product_screen/product_screen.scss',
            'pos_custom_ui/static/src/app/components/orderline/orderline.xml',
            'pos_custom_ui/static/src/app/components/product_card/product_card.xml',
        ],
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
