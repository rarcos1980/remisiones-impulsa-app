import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generar_pdf_remision(datos_remision, partidas, output_path):
    """
    Genera un archivo PDF con formato idéntico a remision.pdf.
    
    datos_remision: dict con claves de encabezado, especialidades, totales, expediente y pagaré.
    partidas: lista de dicts con cantidad, cve_producto, alg, descripcion, lote, precio_unitario, total_partida.
    output_path: ruta donde se guardará el PDF.
    """
    # Configuración de márgenes (0.35 pulgadas para abarcar todo en 1 página)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=25,
        rightMargin=25,
        topMargin=20,
        bottomMargin=20
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    style_normal = ParagraphStyle('NormalSmall', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#1A1A1A'))
    style_bold = ParagraphStyle('BoldSmall', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#1A1A1A'))
    style_header_title = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontSize=12, leading=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#000000'))
    style_remision_title = ParagraphStyle('RemisionTitle', parent=styles['Normal'], fontSize=12, leading=14, fontName='Helvetica-Bold', alignment=2, textColor=colors.HexColor('#1F497D'))
    style_table_header = ParagraphStyle('TableHeader', parent=styles['Normal'], fontSize=8, leading=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7.5, leading=9, textColor=colors.HexColor('#222222'))
    style_cell_center = ParagraphStyle('CellCenter', parent=styles['Normal'], fontSize=7.5, leading=9, alignment=1, textColor=colors.HexColor('#222222'))
    style_cell_right = ParagraphStyle('CellRight', parent=styles['Normal'], fontSize=7.5, leading=9, alignment=2, textColor=colors.HexColor('#222222'))

    # 1. ENCABEZADO (Logo + Empresa + Datos Remisión)
    # Intentar cargar logo si existe
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        img_logo = Image(logo_path, width=1.5*inch, height=0.6*inch)
    else:
        img_logo = Paragraph("<b>IMPULSA<br/>BAJÍO</b>", ParagraphStyle('LogoTxt', fontSize=14, leading=16, textColor=colors.HexColor('#70AD47')))

    txt_empresa = Paragraph(
        "<b>MCR IMPULSO</b><br/>"
        "<font size=7 color='#444444'>"
        "RFC: MIM 180215 3ZA &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; CAMINO A LOS OLVERA NO. 721<br/>"
        "OF. (442) 277 8358 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; LOCAL 7, COL. LOS OLVERA<br/>"
        "EMERGENCIAS: (442) 454 0005 &nbsp;&nbsp; EL PUEBLITO, CORREGIDORA"
        "</font>",
        style_normal
    )
    
    txt_remision = Paragraph(
        "<b><font size=12 color='#1F497D'>REMISIÓN</font></b><br/><br/>"
        f"<b>Folio:</b> <font color='#C00000'>{datos_remision.get('folio', 'REM-00000')}</font><br/>"
        f"<b>Fecha:</b> {datos_remision.get('fecha', datetime.now().strftime('%d/%m/%Y'))}",
        style_normal
    )

    tbl_header = Table(
        [[img_logo, txt_empresa, txt_remision]],
        colWidths=[110, 310, 142]
    )
    tbl_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (2,0), (2,0), 'RIGHT'),
    ]))
    story.append(tbl_header)
    story.append(Spacer(1, 6))

    # 2. DATOS DE CLIENTE Y VENDEDOR
    datos_cli = [
        [
            Paragraph("<b>Cliente:</b>", style_bold),
            Paragraph(datos_remision.get('nombre_cliente', ''), style_normal),
            Paragraph("<b>VENDEDOR:</b>", style_bold),
            Paragraph(datos_remision.get('nombre_vendedor', ''), style_normal)
        ],
        [
            Paragraph("<b>Dirección:</b>", style_bold),
            Paragraph(datos_remision.get('direccion_cliente', ''), style_normal),
            "", ""
        ]
    ]
    tbl_cli = Table(datos_cli, colWidths=[55, 325, 65, 117])
    tbl_cli.setStyle(TableStyle([
        ('SPAN', (1,1), (3,1)),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#E9EDF4')),
        ('BACKGROUND', (1,1), (3,1), colors.HexColor('#E9EDF4')),
        ('BACKGROUND', (3,0), (3,0), colors.HexColor('#E9EDF4')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(tbl_cli)
    story.append(Spacer(1, 8))

    # 3. TABLA DE PARTIDAS (Mínimo 14 filas para llenar espacio visual)
    headers_partidas = [
        Paragraph("Cantidad", style_table_header),
        Paragraph("Cve. Producto", style_table_header),
        Paragraph("ALG", style_table_header),
        Paragraph("Descripcion", style_table_header),
        Paragraph("Lote", style_table_header),
        Paragraph("Precio Unitario", style_table_header),
        Paragraph("Total Partida", style_table_header),
    ]
    
    rows_partidas = [headers_partidas]
    
    # Rellenar con partidas o filas vacías
    total_filas = max(14, len(partidas))
    for i in range(total_filas):
        if i < len(partidas):
            p = partidas[i]
            cant = f"{p.get('cantidad', 0):.2f}" if isinstance(p.get('cantidad'), (int, float)) else str(p.get('cantidad', ''))
            pu = f"${p.get('precio_unitario', 0.0):,.2f}"
            tot = f"${p.get('total_partida', 0.0):,.2f}"
            rows_partidas.append([
                Paragraph(cant, style_cell_center),
                Paragraph(str(p.get('cve_producto', '')), style_cell_center),
                Paragraph(str(p.get('alg', '')), style_cell_center),
                Paragraph(str(p.get('descripcion', '')), style_cell),
                Paragraph(str(p.get('lote', '')), style_cell_center),
                Paragraph(pu, style_cell_right),
                Paragraph(tot, style_cell_right)
            ])
        else:
            rows_partidas.append(["", "", "", "", "", "", ""])

    tbl_partidas = Table(rows_partidas, colWidths=[52, 72, 40, 208, 55, 67, 68])
    
    ts_partidas = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1F497D')),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#B8CCE4')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]
    # Alternar color de filas
    for r in range(1, len(rows_partidas)):
        if r % 2 == 0:
            ts_partidas.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#F2F5F9')))
        else:
            ts_partidas.append(('BACKGROUND', (0, r), (-1, r), colors.white))
            
    tbl_partidas.setStyle(TableStyle(ts_partidas))
    story.append(tbl_partidas)
    story.append(Spacer(1, 6))

    # 4. ESPECIALIDADES (Checkboxes) Y TOTALES
    esp = datos_remision.get('especialidades', {})
    chk = lambda val: "[X]" if val else "[  ]"
    
    txt_especialidades = Paragraph(
        f"{chk(esp.get('electrofisiologia'))} &nbsp; ELECTROFISIOLOGI Y TECNOLOGIAS DE MAPEO<br/>"
        f"{chk(esp.get('radiologia'))} &nbsp; RADIOOGIA INTERVENCIONISTA<br/>"
        f"{chk(esp.get('cardiologia'))} &nbsp; CARDILOGIA INTERVENCIONISTA<br/>"
        f"{chk(esp.get('endovascular'))} &nbsp; EDOVASCULAR PERIFERICO<br/>"
        f"{chk(esp.get('neuromodulacion'))} &nbsp; NEUROMODULACION",
        ParagraphStyle('EspStyle', parent=style_normal, fontSize=7, leading=10)
    )
    
    subtotal = datos_remision.get('subtotal', 0.0)
    descuento_pct = datos_remision.get('descuento_pct', 0.0)
    descuento_monto = datos_remision.get('descuento_monto', 0.0)
    iva = datos_remision.get('iva', 0.0)
    total = datos_remision.get('total', 0.0)
    total_letra = datos_remision.get('total_letra', 'Cero Pesos 00/100 M.N.')

    data_totales = [
        [Paragraph("Descuento %", style_bold), Paragraph(f"{descuento_pct:.0f}%", style_cell_right), Paragraph("Subtotal", style_bold), Paragraph(f"${subtotal:,.2f}", style_cell_right)],
        ["", "", Paragraph("Descuento", style_bold), Paragraph(f"${descuento_monto:,.2f}", style_cell_right)],
        ["", "", Paragraph("IVA (16%)", style_bold), Paragraph(f"${iva:,.2f}", style_cell_right)],
        ["", "", Paragraph("TOTAL", style_bold), Paragraph(f"<b>${total:,.2f}</b>", style_cell_right)]
    ]
    tbl_totales_sub = Table(data_totales, colWidths=[65, 45, 60, 60])
    tbl_totales_sub.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#B8CCE4')),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#DCE6F1')),
        ('BACKGROUND', (2,0), (3,-1), colors.HexColor('#DCE6F1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))

    tbl_esp_tot = Table([[txt_especialidades, tbl_totales_sub]], colWidths=[332, 230])
    tbl_esp_tot.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(tbl_esp_tot)
    story.append(Spacer(1, 4))

    # Total en letras
    tbl_total_letra = Table([[
        Paragraph("<b>Total en letras:</b>", style_bold),
        Paragraph(f"<i>{total_letra}</i>", style_normal)
    ]], colWidths=[80, 482])
    tbl_total_letra.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#1F497D')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(tbl_total_letra)
    story.append(Spacer(1, 6))

    # 5. EXPEDIENTE Y DATOS MÉDICOS
    data_exp = [
        [Paragraph("<b>NOMBRE DEL PACIENTE:</b>", style_bold), Paragraph(datos_remision.get('nombre_paciente', ''), style_normal)],
        [Paragraph("<b>NOMBRE DEL DOCTOR:</b>", style_bold), Paragraph(datos_remision.get('nombre_doctor', ''), style_normal)],
        [Paragraph("<b>EPISODIO:</b>", style_bold), Paragraph(datos_remision.get('episodio', ''), style_normal)],
        [Paragraph("<b>ASEGURADORA:</b>", style_bold), Paragraph(datos_remision.get('aseguradora', ''), style_normal)],
        [Paragraph("<b>DIAGNOSTICO:</b>", style_bold), Paragraph(datos_remision.get('diagnostico', ''), style_normal)],
        [Paragraph("<b>AGENTE:</b>", style_bold), Paragraph(datos_remision.get('agente', ''), style_normal)],
    ]
    tbl_exp = Table(data_exp, colWidths=[120, 442])
    tbl_exp.setStyle(TableStyle([
        ('BACKGROUND', (1,0), (1,-1), colors.HexColor('#E9EDF4')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(tbl_exp)
    story.append(Spacer(1, 6))

    # 6. PAGARÉ LEGAL Y FIRMAS
    txt_pagare_hdr = Paragraph("<b>PAGARE</b>", ParagraphStyle('PagareHdr', parent=style_bold, textColor=colors.white))
    tbl_pagare_hdr = Table([[txt_pagare_hdr]], colWidths=[562])
    tbl_pagare_hdr.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#4F81BD')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(tbl_pagare_hdr)

    txt_pagare_cuerpo = Paragraph(
        f"A TRAVEZ DE ESTE PAGARE YO <b>{datos_remision.get('nombre_cliente', '________________')}</b> ME COMPROMETO A PAGAR INCONDICIONALMENTE "
        f"LA CANTIDAD DE <b>${total:,.2f}</b> A LA ORDEN DE MCR IMPULSO, SA DE CV, DICHA CANTIDAD SERA PAGADA EN MEXICO, QUERETARO "
        f"EN LA FECHA <b>{datos_remision.get('fecha_pagare', datos_remision.get('fecha', datetime.now().strftime('%d/%m/%Y')))}</b> "
        f"EN CASO DE NO CUMPLIR CON EL PAGO EN LA FECHA ACORDADA, SE GENERARA UN INTERES MORATORIO DEL 5% MENSUAL.",
        ParagraphStyle('PagareBody', parent=style_normal, fontSize=7, leading=9)
    )
    story.append(Spacer(1, 3))
    story.append(txt_pagare_cuerpo)
    story.append(Spacer(1, 15))

    # Firmas
    firma_agente_path = datos_remision.get('firma_agente_path')
    firma_cliente_path = datos_remision.get('firma_cliente_path')
    
    img_firma_agente = Image(firma_agente_path, width=1.5*inch, height=0.4*inch) if firma_agente_path and os.path.exists(firma_agente_path) else Paragraph("", style_normal)
    img_firma_cliente = Image(firma_cliente_path, width=1.5*inch, height=0.4*inch) if firma_cliente_path and os.path.exists(firma_cliente_path) else Paragraph("", style_normal)

    data_firmas = [
        [img_firma_agente, img_firma_cliente],
        [
            Paragraph("____________________________________________", style_cell_center),
            Paragraph("____________________________________________", style_cell_center)
        ],
        [
            Paragraph(f"<b>{datos_remision.get('nombre_vendedor', 'AGENTE')}</b><br/>AGENTE", style_cell_center),
            Paragraph("RECIBI Y ACEPTO", style_cell_center)
        ]
    ]
    tbl_firmas = Table(data_firmas, colWidths=[281, 281])
    tbl_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(tbl_firmas)

    # Construir documento
    doc.build(story)
    print(f"PDF generado exitosamente en: {output_path}")

if __name__ == "__main__":
    # Test de generación
    datos_demo = {
        'folio': 'REM-00056',
        'fecha': '20/08/2026',
        'nombre_cliente': 'CLINICA HOSPITAL SAN JOSE DE QUERETARO',
        'direccion_cliente': 'AV. CONSTITUYENTES NO. 102 COL. CENTRO',
        'nombre_vendedor': 'DANIEL ALEJANDRO VIELMA TELLE',
        'especialidades': {'electrofisiologia': True, 'cardiologia': True},
        'subtotal': 15500.00,
        'descuento_pct': 0.0,
        'descuento_monto': 0.0,
        'iva': 2480.00,
        'total': 17980.00,
        'total_letra': 'Diecisiete Mil Novecientos Ochenta Pesos 00/100 M.N.',
        'nombre_paciente': 'JUAN PEREZ LOPEZ',
        'nombre_doctor': 'DR. ROBERTO MARTINEZ',
        'episodio': 'EP-99482',
        'aseguradora': 'AXA SEGUROS',
        'diagnostico': 'ESTENOSIS CORONARIA',
        'agente': 'DANIEL ALEJANDRO VIELMA TELLE',
        'fecha_pagare': '20/08/2026'
    }
    partidas_demo = [
        {'cantidad': 1, 'cve_producto': 'MAP-001', 'alg': 'A1', 'descripcion': 'CATETER DE MAPEO ELECTROFISIOLOGICO 10 POLOS', 'lote': 'L2026-08', 'precio_unitario': 10500.00, 'total_partida': 10500.00},
        {'cantidad': 2, 'cve_producto': 'INTRO-02', 'alg': 'B2', 'descripcion': 'INTRODUCTOR VASCULAR 6F', 'lote': 'L2026-05', 'precio_unitario': 2500.00, 'total_partida': 5000.00}
    ]
    pdf_out = os.path.join(os.path.dirname(__file__), "remision_test_generada.pdf")
    generar_pdf_remision(datos_demo, partidas_demo, pdf_out)

def generar_pdf_ticket_58mm(datos_remision, partidas, output_path):
    """
    Genera un archivo PDF con formato de ticket para impresora térmica de 58mm.
    El ancho total es de aprox. 58mm (164 puntos).
    """
    from reportlab.lib.units import mm
    import sae_connector
    
    cfg = sae_connector.load_config()
    t_empresa = cfg.get('ticket_empresa', 'MCR IMPULSO')
    t_rfc = cfg.get('ticket_rfc', 'RFC: MIM 180215 3ZA')
    t_dir = cfg.get('ticket_dir', 'CAMINO A LOS OLVERA NO. 721\nCOL. LOS OLVERA\nEL PUEBLITO, CORREGIDORA').replace('\n', '<br/>')
    t_tel = cfg.get('ticket_tel', 'TEL: (442) 277 8358')
    
    ancho_ticket = 58 * mm
    # Altura dinámica: 120 (cabecera) + 80 (totales y pie) + 20 por partida
    alto_ticket = (120 + 80 + (len(partidas) * 15)) * mm
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=(ancho_ticket, alto_ticket),
        leftMargin=3*mm,
        rightMargin=3*mm,
        topMargin=5*mm,
        bottomMargin=5*mm,
        showBoundary=0
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    style_center = ParagraphStyle('Center', parent=styles['Normal'], fontSize=7, leading=8, alignment=1, textColor=colors.black)
    style_left = ParagraphStyle('Left', parent=styles['Normal'], fontSize=7, leading=8, alignment=0, textColor=colors.black)
    style_right = ParagraphStyle('Right', parent=styles['Normal'], fontSize=7, leading=8, alignment=2, textColor=colors.black)
    style_bold_center = ParagraphStyle('BoldCenter', parent=styles['Normal'], fontSize=8, leading=9, fontName='Helvetica-Bold', alignment=1, textColor=colors.black)
    style_bold_left = ParagraphStyle('BoldLeft', parent=styles['Normal'], fontSize=7, leading=8, fontName='Helvetica-Bold', alignment=0, textColor=colors.black)
    
    # 1. Cabecera
    story.append(Paragraph(f"<b>{t_empresa}</b>", style_bold_center))
    story.append(Paragraph(t_rfc, style_center))
    story.append(Paragraph(t_dir, style_center))
    story.append(Paragraph(t_tel, style_center))
    story.append(Spacer(1, 3*mm))
    
    # 2. Datos de Remisión
    story.append(Paragraph(f"<b>TICKET VENTA</b>", style_bold_center))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(f"<b>Folio:</b> {datos_remision.get('folio', '')}", style_left))
    story.append(Paragraph(f"<b>Fecha:</b> {datos_remision.get('fecha', '')}", style_left))
    story.append(Paragraph(f"<b>Cliente:</b> {datos_remision.get('nombre_cliente', '')}", style_left))
    story.append(Paragraph(f"<b>Vend:</b> {datos_remision.get('nombre_vendedor', '')}", style_left))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("-" * 35, style_center))
    
    # 3. Partidas (Tabla simplificada)
    data_partidas = []
    for p in partidas:
        cant = f"{p.get('cantidad', 1):.0f}"
        desc = str(p.get('descripcion', ''))[:15] # Truncar para que quepa
        tot = f"${p.get('total_partida', 0):,.2f}"
        data_partidas.append([
            Paragraph(f"{cant}x {desc}", style_left),
            Paragraph(tot, style_right)
        ])
        
    if data_partidas:
        tbl_partidas = Table(data_partidas, colWidths=[33*mm, 17*mm])
        tbl_partidas.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(tbl_partidas)
        
    story.append(Paragraph("-" * 35, style_center))
    
    # 4. Totales
    total = datos_remision.get('total', 0.0)
    data_totales = [
        [Paragraph("<b>TOTAL:</b>", style_bold_left), Paragraph(f"<b>${total:,.2f}</b>", style_right)]
    ]
    tbl_tot = Table(data_totales, colWidths=[20*mm, 30*mm])
    tbl_tot.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(tbl_tot)
    story.append(Spacer(1, 4*mm))
    
    # 5. Pie de ticket
    story.append(Paragraph("GRACIAS POR SU COMPRA", style_bold_center))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("Este documento no es un<br/>comprobante fiscal.", style_center))
    
    doc.build(story)
    print(f"Ticket generado en: {output_path}")

if __name__ == "__main__":
    pdf_ticket_out = os.path.join(os.path.dirname(__file__), "ticket_test_generado.pdf")
    generar_pdf_ticket_58mm(datos_demo, partidas_demo, pdf_ticket_out)
