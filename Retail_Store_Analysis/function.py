#libs:

import pandas as pd 
from datetime import datetime
import time
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')


def data_pre_processing(df):
    
    df_temp = df.rename(columns = {'InvoiceNo':'invoice_id','StockCode': 'stock_code', 'Description':'description',
                          'Quantity': 'quantity','InvoiceDate':'invoice_date','UnitPrice': 'unit_price',
                          'CustomerID': 'customer_id','Country':'country'})

    rt = df_temp.dropna(subset=["description","customer_id"]).reset_index(drop = True)
    rt['invoice_id']= rt['invoice_id'].apply(str)

    #Order status:

    rt['order_status'] = rt['invoice_id'].apply(lambda x: 'Cancelled' if x.find('C') != -1 else 'Approved')

    #total of sales in sterling:

    rt['sales(£)'] = rt['quantity']*rt['unit_price']
    rt['sales(£)_abs'] = rt['sales(£)'].abs()

    rt['sales(£)'] = rt['quantity']*rt['unit_price']
    rt['quantity_abs'] = rt['quantity'].abs()

    #datetime split: 

    rt['time'] = rt['invoice_date'].apply(lambda x: x.strftime('%H:%M:%S'))
    rt['hour'] = rt['invoice_date'].apply(lambda x: x.strftime('%H'))

    rt['date'] = rt['invoice_date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    rt['date'] = pd.to_datetime(rt['date'], format = '%Y-%m-%d')

    rt['month'] = rt['invoice_date'].apply(lambda x: x.strftime('%Y-%m'))
    rt['year'] = rt['invoice_date'].apply(lambda x: x.strftime('%Y'))

    #Filter only the year 2011:

    rt = rt[rt.year == '2011']

    return rt



def finance_and_sales_report(rt):


    #Finance report:

    acc = rt.groupby('order_status')['quantity_abs','sales(£)_abs'].sum().reset_index() 
    cus = rt.groupby('order_status')['customer_id'].count().reset_index()

    financial = acc.merge(cus, on = 'order_status', how = 'left')

    financial['sales(£100k)'] = round((financial['sales(£)_abs']/100000),2)
    financial['quantity_abs(100k)'] = round((financial['quantity_abs']/100000),2)

    financial = financial.set_index('order_status')

    financial = financial.append(financial.sum().rename('Total')).reset_index()

    financial['avg_ticket'] = round((financial['sales(£)_abs']/financial['customer_id']),2)

    financial_final = financial[['order_status','quantity_abs(100k)','sales(£100k)','customer_id','avg_ticket']]

    #Sales Analytics:

    sales_year = rt.groupby('month')['sales(£)_abs','quantity_abs'].sum().reset_index()

    sales_year['sales(%)'] = round((sales_year['sales(£)_abs']/sales_year['sales(£)_abs'].sum()*100),2)

    sales_year['quantity(%)'] = round((sales_year['quantity_abs']/sales_year['quantity_abs'].sum()*100),2)
    
    return financial_final, sales_year


def customer_and_product_behavior(rt):
    
    #Country sales and product distribution:

    country= rt.groupby(['country'])['quantity','sales(£)'].sum().reset_index()

    country['sales(£k)'] = round((country['sales(£)']/1000),2)

    country = country.sort_values('sales(£k)',ascending = False)

    country['sales(%)'] = round((country['sales(£k)']/country['sales(£k)'].sum()*100),2)

    country_final = country[['country', 'quantity', 'sales(£k)', 'sales(%)']]
    
    country_top10 = country_final.head(10)


    #returned invoices analysis:

    ret_temp = rt.groupby(['order_status'])['quantity_abs','sales(£)_abs'].sum().reset_index()
    ret_aux = rt.groupby(['order_status'])['invoice_id'].count().reset_index()
    ret_temp = ret_temp.merge(ret_aux, how = 'left', on = 'order_status')

    ret_temp['sales(£k)'] = round((ret_temp['sales(£)_abs']/100000),2)
    ret_temp['sales(%)'] = round((ret_temp['sales(£)_abs']/ret_temp['sales(£)_abs'].sum()*100),2)

    ret_temp['quantity(%)'] = round((ret_temp['quantity_abs']/ret_temp['quantity_abs'].sum()*100),2)

    ret_temp['invoice(%)'] = round((ret_temp['invoice_id']/ret_temp['invoice_id'].sum()*100),2)

    returned = ret_temp[['order_status','quantity_abs','invoice_id','sales(£k)','sales(%)','quantity(%)','invoice(%)']]


    #repurchase rate:

    cust_temp = rt.customer_id.value_counts().reset_index()

    cust_aux = cust_temp[cust_temp.customer_id >= 2]

    repurchase_rate = round((len(cust_aux)/len(cust_temp)*100),2)

    # Time people often purchase online:

    time = rt.rename(columns = {'hour':'Time'})
    
    #best sellers:
    
    best = rt.groupby(['stock_code','description'])['quantity_abs'].sum().reset_index().sort_values(['quantity_abs'], 
                                                                                              ascending = False)
    top10_best = best.head(10).reset_index(drop = True)
    
    top10_best = top10_best.reindex(index=top10_best.index[::-1])
    
    #products best revenue:
    
    prd_sales = rt.groupby(['description'])['sales(£)_abs'].sum().reset_index()

    prd_sales = prd_sales.sort_values('sales(£)_abs', ascending = False)
    
    #many items each customer buy by invoice:
    
    item = rt.groupby('invoice_id')['quantity'].mean().reset_index()
    
    return country_top10, time, returned, repurchase_rate, top10_best, prd_sales,item


def charts(sales_year,time, prd_sales, top10_best, item):
    
    #Sales Chart:
    
    sales_line = go.Figure()
    sales_line.add_trace(go.Scatter(x=sales_year["month"], y=sales_year['sales(%)'],
                mode='lines+markers',
                name='Total Sales £ (%)'))
    sales_line.add_trace(go.Scatter(x=sales_year["month"], y=sales_year['quantity(%)'],
                mode='lines+markers',
                name='Quantity Item(%)'))
    sales_line.update_layout(title='Financial and Sales Report', xaxis_title='Month')
    
    #Customer Purchase Behavior Histogram:
    time_his = px.histogram(time, x="Time", range_x = (5,25),
                            title='Time frequency that the customer usually buys').update_layout(bargap=0.1)
    
    #top10 product best revenue:
    
    sales10_bar = px.bar(prd_sales.head(10), x="description", y="sales(£)_abs",
                 labels = {"sales(£)_abs":'Sales (£)','description':'Description'}, 
                         title="Top 10 product revenue", text = 'sales(£)_abs') 
    sales10_bar.update_traces(texttemplate='%{text:.2s}', textposition='inside')
    sales10_bar.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    
    #top10 product best sells: 
    
    top10sel_bar = px.bar(top10_best, y='description', x='quantity_abs', text = 'quantity_abs', orientation='h',
                      title="Top 10 product volume", labels = {"quantity_abs":'Quantity','description':'Description'})
    top10sel_bar.update_traces(texttemplate='%{text:.2s}', textposition='inside')
    top10sel_bar.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    
    #many items each customer buy by invoice:
    
    item_hist = px.histogram(item, x="quantity" , nbins = 100000 , range_x = (0, 80),title='Average of items by invoice',
                             labels = {'quantity':'Quantity'}).update_layout(bargap=0.1)


    

    return sales_line, time_his, sales10_bar, top10sel_bar, item_hist