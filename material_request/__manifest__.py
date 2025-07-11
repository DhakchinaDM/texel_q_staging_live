# -*- coding: utf-8 -*-
##############################################################################
{
    'name': 'Material Request And Approval',
    'version': '17.0.6.22',
    'category': 'Warehouses',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    #'images': ['static/description/banner.gif'],
    'price': '60',
    #'price': '49.82',
    'description': """ The Material requisition is a systematic process facilitating the request and acquisition of stock
    items from a designated store. It begins with a user submitting a request for a specific quantity of items required 
    for their department or project. Upon receiving the request, the responsible team in charge of managing inventory 
    evaluates the availability of the requested items.Based on the availability, the team updates the status of the
    request, either approving it for further processing or rejecting it due to insufficient stock. If approved,
    the request moves to authorized personnel for final approval. These authorized individuals review the request 
    and decide whether to give their approval or reject it.Once approved, if the items are in stock, they are promptly 
    dispatched to the specified departments or individuals. However, if the requested items are not available in the 
    inventory, the procurement process is initiated to purchase them. Once the procurement is completed, the items 
    are then dispatched to the respective departments.Throughout this entire process, every action taken, including
    approvals, rejections, dispatches, and procurement, is meticulously tracked and recorded. Remarks and updates 
    regarding the status of each request are captured, providing transparency and accountability. This information
    is displayed in a ribbon status format on both tree and form views, ensuring that users are promptly notified 
    of any updates or changes to their requests. """,
    'summary': 'Material requisition enables users to request a specific amount of stock from the designated store team'
    ' in charge. Upon receiving the request, the team in charge checks the availability of the requested items'
    ' and updates the status accordingly, either proceeding with the request or rejecting it. Authorized '
    'personnel then receive approval requests from the material requester, where they can choose to approve '
    'or reject based on various factors including stock availability. If the requested stock is available, '
    'it is dispatched to the specified departments. If not, the purchase process is initiated, followed by '
    'dispatch to the departments upon completion. Throughout this process, every action is tracked and remarks'
    ' are captured, updating the status as ribbon status on the tree and form view to notify '
    'the users effectively.',
    'author': 'AppsComp Widgets Pvt Ltd',
    'website': 'www.appscomp.com',
    'depends': ['account', 'stock', 'product', 'purchase', 'hr', 'base','quality_extension','inventory_extended'],
    'data': [
        'security/ir.model.access.csv',
        'security/user_group.xml',
        'views/material_request_view.xml',
        'views/delivery_order.xml',
        'wizard/add_rfq_view.xml',
        'wizard/request_remarks.xml',
    ],
    'installable': True,
    'currency': 'EUR',
    'active': True,

}
