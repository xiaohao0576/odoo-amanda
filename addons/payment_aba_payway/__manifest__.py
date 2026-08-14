{
    'name': 'ABA PayWay for Odoo eCommerce',
    'countries': ['KH'],
    'version': '1.0',
    'author': 'ABA Bank',
    'category': 'Accounting/Payment Providers',
    'summary': 'Display payway payment for e-commerce website.',
    'description': """
        This module allows you to display ABA PayWay QR payment option on your e-commerce website.
    """,
    'depends': ['payment'],
    'external_dependencies': {
        'python': ['cryptography']
    },
    'data': [
        'views/aba_payway_payment_provider_templates.xml',
        'views/payment_provider_views.xml',
        
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',

        'wizards/payment_capture_wizard_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_aba_payway/static/src/**/*',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
    'images': [
        'static/description/banner.gif',
    ],
} # pyright: ignore[reportUnusedExpression]