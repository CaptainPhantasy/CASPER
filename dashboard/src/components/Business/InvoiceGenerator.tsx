import * as React from "react";
import { useState, useCallback, useMemo } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import {
  CreditCardIcon,
  PlusIcon,
  TrashIcon,
  CalendarDaysIcon,
  BuildingOfficeIcon,
  UserIcon,
  CalculatorIcon,
  DocumentTextIcon,
  ArrowDownTrayIcon
} from "@heroicons/react/24/outline";
import { cn } from "@/lib/utils";

interface InvoiceItem {
  id: string;
  description: string;
  quantity: number;
  rate: number;
  amount: number;
}

interface ClientInfo {
  name: string;
  email: string;
  address: string;
  company: string;
}

interface CompanyInfo {
  name: string;
  address: string;
  email: string;
  phone: string;
  taxId: string;
}

interface InvoiceData {
  invoiceNumber: string;
  issueDate: string;
  dueDate: string;
  client: ClientInfo;
  company: CompanyInfo;
  items: InvoiceItem[];
  notes: string;
  taxRate: number;
  currency: string;
  status: 'draft' | 'sent' | 'paid' | 'overdue';
}

const CURRENCIES = [
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'EUR', symbol: '€', name: 'Euro' },
  { code: 'GBP', symbol: '£', name: 'British Pound' },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar' },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar' }
];

const DEFAULT_COMPANY_INFO: CompanyInfo = {
  name: 'CASPER Prime Development',
  address: '123 Innovation Drive\nTech City, TC 12345',
  email: 'billing@casperprime.dev',
  phone: '+1 (555) 123-4567',
  taxId: 'TAX-ID-123456789'
};

const STATUS_COLORS = {
  draft: 'bg-gray-500',
  sent: 'bg-blue-500',
  paid: 'bg-green-500',
  overdue: 'bg-red-500'
};

const generateInvoiceNumber = (): string => {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
  return `INV-${year}${month}-${random}`;
};

const formatDate = (date: string): string => {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
};

export function InvoiceGenerator() {
  const { toast } = useToast();
  const [invoiceData, setInvoiceData] = useState<InvoiceData>({
    invoiceNumber: generateInvoiceNumber(),
    issueDate: new Date().toISOString().split('T')[0],
    dueDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    client: {
      name: '',
      email: '',
      address: '',
      company: ''
    },
    company: DEFAULT_COMPANY_INFO,
    items: [
      {
        id: '1',
        description: '',
        quantity: 1,
        rate: 0,
        amount: 0
      }
    ],
    notes: '',
    taxRate: 0,
    currency: 'USD',
    status: 'draft'
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);

  const selectedCurrency = CURRENCIES.find(c => c.code === invoiceData.currency);

  const calculations = useMemo(() => {
    const subtotal = invoiceData.items.reduce((sum, item) => sum + item.amount, 0);
    const taxAmount = subtotal * (invoiceData.taxRate / 100);
    const total = subtotal + taxAmount;

    return {
      subtotal,
      taxAmount,
      total
    };
  }, [invoiceData.items, invoiceData.taxRate]);

  const handleInputChange = useCallback((field: keyof InvoiceData, value: any) => {
    setInvoiceData(prev => ({ ...prev, [field]: value }));
  }, []);

  const handleClientChange = useCallback((field: keyof ClientInfo, value: string) => {
    setInvoiceData(prev => ({
      ...prev,
      client: { ...prev.client, [field]: value }
    }));
  }, []);

  const handleCompanyChange = useCallback((field: keyof CompanyInfo, value: string) => {
    setInvoiceData(prev => ({
      ...prev,
      company: { ...prev.company, [field]: value }
    }));
  }, []);

  const handleItemChange = useCallback((id: string, field: keyof InvoiceItem, value: any) => {
    setInvoiceData(prev => ({
      ...prev,
      items: prev.items.map(item => {
        if (item.id === id) {
          const updatedItem = { ...item, [field]: value };
          // Recalculate amount when quantity or rate changes
          if (field === 'quantity' || field === 'rate') {
            updatedItem.amount = updatedItem.quantity * updatedItem.rate;
          }
          return updatedItem;
        }
        return item;
      })
    }));
  }, []);

  const addItem = useCallback(() => {
    const newItem: InvoiceItem = {
      id: Date.now().toString(),
      description: '',
      quantity: 1,
      rate: 0,
      amount: 0
    };
    setInvoiceData(prev => ({
      ...prev,
      items: [...prev.items, newItem]
    }));
  }, []);

  const removeItem = useCallback((id: string) => {
    setInvoiceData(prev => ({
      ...prev,
      items: prev.items.filter(item => item.id !== id)
    }));
  }, []);

  const validateInvoice = (): boolean => {
    if (!invoiceData.client.name.trim()) {
      toast({
        title: "Validation Error",
        description: "Client name is required",
        variant: "destructive"
      });
      return false;
    }

    if (!invoiceData.client.email.trim()) {
      toast({
        title: "Validation Error",
        description: "Client email is required",
        variant: "destructive"
      });
      return false;
    }

    if (invoiceData.items.length === 0 || invoiceData.items.every(item => !item.description.trim())) {
      toast({
        title: "Validation Error",
        description: "At least one invoice item is required",
        variant: "destructive"
      });
      return false;
    }

    return true;
  };

  const generateInvoice = async () => {
    if (!validateInvoice()) return;

    setIsGenerating(true);

    try {
      // Simulate invoice generation
      setTimeout(() => {
        setIsGenerating(false);
        setPreviewMode(true);
        toast({
          title: "Invoice Generated",
          description: `Invoice ${invoiceData.invoiceNumber} created successfully`,
        });
      }, 2000);
    } catch (error) {
      console.error('Error generating invoice:', error);
      setIsGenerating(false);
      toast({
        title: "Generation Failed",
        description: "Failed to generate invoice. Please try again.",
        variant: "destructive"
      });
    }
  };

  const exportInvoice = (format: 'pdf' | 'html' | 'json') => {
    toast({
      title: `Export ${format.toUpperCase()}`,
      description: `Exporting invoice as ${format.toUpperCase()}...`
    });

    // Simulate export
    setTimeout(() => {
      toast({
        title: "Export Complete",
        description: `Invoice exported as ${format.toUpperCase()}`
      });
    }, 1500);
  };

  const sendInvoice = () => {
    setInvoiceData(prev => ({ ...prev, status: 'sent' }));
    toast({
      title: "Invoice Sent",
      description: `Invoice sent to ${invoiceData.client.email}`,
    });
  };

  const InvoicePreview = () => (
    <div className="bg-white p-8 border rounded-lg shadow-sm space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">INVOICE</h1>
          <p className="text-xl text-gray-600 mt-1">#{invoiceData.invoiceNumber}</p>
        </div>
        <Badge className={cn("text-white", STATUS_COLORS[invoiceData.status])}>
          {invoiceData.status.toUpperCase()}
        </Badge>
      </div>

      {/* Company & Client Info */}
      <div className="grid grid-cols-2 gap-8">
        <div>
          <h3 className="font-semibold text-gray-900 mb-2">From:</h3>
          <div className="text-gray-600">
            <div className="font-medium">{invoiceData.company.name}</div>
            <div className="whitespace-pre-line text-sm">{invoiceData.company.address}</div>
            <div className="text-sm">{invoiceData.company.email}</div>
            <div className="text-sm">{invoiceData.company.phone}</div>
            {invoiceData.company.taxId && (
              <div className="text-sm">Tax ID: {invoiceData.company.taxId}</div>
            )}
          </div>
        </div>

        <div>
          <h3 className="font-semibold text-gray-900 mb-2">Bill To:</h3>
          <div className="text-gray-600">
            <div className="font-medium">{invoiceData.client.name}</div>
            {invoiceData.client.company && (
              <div className="text-sm">{invoiceData.client.company}</div>
            )}
            <div className="whitespace-pre-line text-sm">{invoiceData.client.address}</div>
            <div className="text-sm">{invoiceData.client.email}</div>
          </div>
        </div>
      </div>

      {/* Dates */}
      <div className="grid grid-cols-2 gap-8">
        <div>
          <span className="font-semibold text-gray-700">Issue Date:</span>
          <div className="text-gray-600">{formatDate(invoiceData.issueDate)}</div>
        </div>
        <div>
          <span className="font-semibold text-gray-700">Due Date:</span>
          <div className="text-gray-600">{formatDate(invoiceData.dueDate)}</div>
        </div>
      </div>

      {/* Items Table */}
      <div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-left">Description</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead className="text-right">Rate</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoiceData.items.map(item => (
              <TableRow key={item.id}>
                <TableCell className="text-left">{item.description}</TableCell>
                <TableCell className="text-right">{item.quantity}</TableCell>
                <TableCell className="text-right">
                  {selectedCurrency?.symbol}{item.rate.toFixed(2)}
                </TableCell>
                <TableCell className="text-right">
                  {selectedCurrency?.symbol}{item.amount.toFixed(2)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Totals */}
      <div className="flex justify-end">
        <div className="w-64 space-y-2">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal:</span>
            <span>{selectedCurrency?.symbol}{calculations.subtotal.toFixed(2)}</span>
          </div>
          {invoiceData.taxRate > 0 && (
            <div className="flex justify-between text-gray-600">
              <span>Tax ({invoiceData.taxRate}%):</span>
              <span>{selectedCurrency?.symbol}{calculations.taxAmount.toFixed(2)}</span>
            </div>
          )}
          <Separator />
          <div className="flex justify-between text-lg font-semibold text-gray-900">
            <span>Total:</span>
            <span>{selectedCurrency?.symbol}{calculations.total.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Notes */}
      {invoiceData.notes && (
        <div>
          <h3 className="font-semibold text-gray-900 mb-2">Notes:</h3>
          <div className="text-gray-600 text-sm whitespace-pre-line">
            {invoiceData.notes}
          </div>
        </div>
      )}
    </div>
  );

  if (previewMode) {
    return (
      <div className="flex flex-col space-y-6 p-4">
        {/* Header */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CreditCardIcon className="h-6 w-6 text-emerald-500" />
                <CardTitle className="text-emerald-700">Invoice Preview</CardTitle>
              </div>
              <div className="flex space-x-2">
                <Button variant="outline" onClick={() => setPreviewMode(false)}>
                  Edit Invoice
                </Button>
                <Button onClick={() => exportInvoice('pdf')}>
                  <ArrowDownTrayIcon className="mr-2 h-4 w-4" />
                  Export PDF
                </Button>
                <Button onClick={sendInvoice} className="bg-emerald-600 hover:bg-emerald-700">
                  Send Invoice
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>

        <InvoicePreview />

        <Card>
          <CardFooter className="flex justify-center space-x-4">
            <Button variant="outline" onClick={() => exportInvoice('html')}>
              Export HTML
            </Button>
            <Button variant="outline" onClick={() => exportInvoice('json')}>
              Export JSON
            </Button>
            <Button variant="outline" onClick={() => setPreviewMode(false)}>
              Edit Invoice
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-6 p-4">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <CreditCardIcon className="h-6 w-6 text-emerald-500" />
            <CardTitle className="text-emerald-700">Professional Invoice Generator</CardTitle>
          </div>
          <CardDescription>
            Create and customize professional invoices for your business
          </CardDescription>
        </CardHeader>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Invoice Details */}
        <div className="space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Invoice Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="invoiceNumber">Invoice Number</Label>
                  <Input
                    id="invoiceNumber"
                    value={invoiceData.invoiceNumber}
                    onChange={(e) => handleInputChange('invoiceNumber', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="currency">Currency</Label>
                  <Select value={invoiceData.currency} onValueChange={(value) => handleInputChange('currency', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CURRENCIES.map(currency => (
                        <SelectItem key={currency.code} value={currency.code}>
                          {currency.symbol} {currency.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="issueDate">Issue Date</Label>
                  <div className="relative">
                    <CalendarDaysIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="issueDate"
                      type="date"
                      value={invoiceData.issueDate}
                      onChange={(e) => handleInputChange('issueDate', e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dueDate">Due Date</Label>
                  <div className="relative">
                    <CalendarDaysIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="dueDate"
                      type="date"
                      value={invoiceData.dueDate}
                      onChange={(e) => handleInputChange('dueDate', e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Client Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <UserIcon className="mr-2 h-5 w-5" />
                Client Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="clientName">Client Name *</Label>
                  <Input
                    id="clientName"
                    placeholder="John Smith"
                    value={invoiceData.client.name}
                    onChange={(e) => handleClientChange('name', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="clientEmail">Client Email *</Label>
                  <Input
                    id="clientEmail"
                    type="email"
                    placeholder="john@example.com"
                    value={invoiceData.client.email}
                    onChange={(e) => handleClientChange('email', e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="clientCompany">Company (Optional)</Label>
                <Input
                  id="clientCompany"
                  placeholder="Acme Corporation"
                  value={invoiceData.client.company}
                  onChange={(e) => handleClientChange('company', e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="clientAddress">Address</Label>
                <Textarea
                  id="clientAddress"
                  placeholder="123 Client Street&#10;City, State 12345"
                  value={invoiceData.client.address}
                  onChange={(e) => handleClientChange('address', e.target.value)}
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Company Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <BuildingOfficeIcon className="mr-2 h-5 w-5" />
                Your Company Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="companyName">Company Name</Label>
                <Input
                  id="companyName"
                  value={invoiceData.company.name}
                  onChange={(e) => handleCompanyChange('name', e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="companyEmail">Email</Label>
                  <Input
                    id="companyEmail"
                    type="email"
                    value={invoiceData.company.email}
                    onChange={(e) => handleCompanyChange('email', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="companyPhone">Phone</Label>
                  <Input
                    id="companyPhone"
                    value={invoiceData.company.phone}
                    onChange={(e) => handleCompanyChange('phone', e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="companyAddress">Address</Label>
                <Textarea
                  id="companyAddress"
                  value={invoiceData.company.address}
                  onChange={(e) => handleCompanyChange('address', e.target.value)}
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="taxId">Tax ID (Optional)</Label>
                <Input
                  id="taxId"
                  value={invoiceData.company.taxId}
                  onChange={(e) => handleCompanyChange('taxId', e.target.value)}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Invoice Items & Summary */}
        <div className="space-y-6">
          {/* Invoice Items */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">Invoice Items</CardTitle>
                <Button onClick={addItem} size="sm">
                  <PlusIcon className="mr-2 h-4 w-4" />
                  Add Item
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {invoiceData.items.map((item, index) => (
                  <Card key={item.id}>
                    <CardContent className="pt-4">
                      <div className="space-y-3">
                        <div className="flex justify-between items-center">
                          <Label className="font-medium">Item {index + 1}</Label>
                          {invoiceData.items.length > 1 && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => removeItem(item.id)}
                            >
                              <TrashIcon className="h-4 w-4" />
                            </Button>
                          )}
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor={`description-${item.id}`} className="text-xs">
                            Description
                          </Label>
                          <Input
                            id={`description-${item.id}`}
                            placeholder="Web development services..."
                            value={item.description}
                            onChange={(e) => handleItemChange(item.id, 'description', e.target.value)}
                          />
                        </div>

                        <div className="grid grid-cols-3 gap-2">
                          <div className="space-y-2">
                            <Label htmlFor={`quantity-${item.id}`} className="text-xs">
                              Quantity
                            </Label>
                            <Input
                              id={`quantity-${item.id}`}
                              type="number"
                              min="0"
                              step="0.01"
                              value={item.quantity}
                              onChange={(e) => handleItemChange(item.id, 'quantity', parseFloat(e.target.value) || 0)}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor={`rate-${item.id}`} className="text-xs">
                              Rate ({selectedCurrency?.symbol})
                            </Label>
                            <Input
                              id={`rate-${item.id}`}
                              type="number"
                              min="0"
                              step="0.01"
                              value={item.rate}
                              onChange={(e) => handleItemChange(item.id, 'rate', parseFloat(e.target.value) || 0)}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs">Amount</Label>
                            <div className="h-10 px-3 py-2 bg-muted rounded-md text-sm flex items-center">
                              {selectedCurrency?.symbol}{item.amount.toFixed(2)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Tax & Total */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <CalculatorIcon className="mr-2 h-5 w-5" />
                Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="taxRate">Tax Rate (%)</Label>
                <Input
                  id="taxRate"
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  value={invoiceData.taxRate}
                  onChange={(e) => handleInputChange('taxRate', parseFloat(e.target.value) || 0)}
                />
              </div>

              <Separator />

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Subtotal:</span>
                  <span>{selectedCurrency?.symbol}{calculations.subtotal.toFixed(2)}</span>
                </div>
                {invoiceData.taxRate > 0 && (
                  <div className="flex justify-between text-sm">
                    <span>Tax ({invoiceData.taxRate}%):</span>
                    <span>{selectedCurrency?.symbol}{calculations.taxAmount.toFixed(2)}</span>
                  </div>
                )}
                <Separator />
                <div className="flex justify-between text-lg font-semibold">
                  <span>Total:</span>
                  <span>{selectedCurrency?.symbol}{calculations.total.toFixed(2)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <DocumentTextIcon className="mr-2 h-5 w-5" />
                Additional Notes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                placeholder="Payment terms, thank you note, or any additional information..."
                value={invoiceData.notes}
                onChange={(e) => handleInputChange('notes', e.target.value)}
                rows={4}
              />
            </CardContent>
          </Card>

          {/* Generate Button */}
          <Card>
            <CardFooter>
              <Button
                onClick={generateInvoice}
                disabled={isGenerating}
                className="w-full bg-emerald-600 hover:bg-emerald-700"
              >
                <CreditCardIcon className="mr-2 h-4 w-4" />
                {isGenerating ? 'Generating...' : 'Generate Invoice'}
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );
}