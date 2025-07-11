from odoo import fields, models, api, _


class CategoryApproval(models.Model):
    _name = 'category.approval'
    _description = 'Category Approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    no_of_approvers = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ], string='No of Approvers', default='1')
    approver_one = fields.Many2one('res.users', string="First Approver")
    approver_two = fields.Many2one('res.users', string="Second Approver")
    approver_three = fields.Many2one('res.users', string="Third Approver")
    approver_four = fields.Many2one('res.users', string="Fourth Approver")
    approver_five = fields.Many2one('res.users', string="Fifth Approver")
    purchase_limit_one = fields.Float(string='First Approver Purchase Limit')
    purchase_limit_two = fields.Float(string='Second Approver Purchase Limit')
    purchase_limit_three = fields.Float(string='Third Approver Purchase Limit')
    purchase_limit_four = fields.Float(string='Fourth Approver Purchase Limit')
    purchase_limit_five = fields.Float(string='Fifth Approver Purchase Limit')

    # the below function is used to remove approver value when changing the no of approvers
    @api.onchange('no_of_approvers')
    def _onchange_remove_approver(self):
        if self.no_of_approvers == '1':
            self.approver_two = False
            self.approver_three = False
            self.approver_four = False
            self.approver_five = False
        elif self.no_of_approvers == '2':
            self.approver_three = False
            self.approver_four = False
            self.approver_five = False
        elif self.no_of_approvers == '3':
            self.approver_four = False
            self.approver_five = False
        elif self.no_of_approvers == '4':
            self.approver_five = False
