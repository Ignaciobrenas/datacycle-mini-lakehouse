# 🏛️ Datacycle Mini Lakehouse

![Python](https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-data-150458?logo=pandas)
![Architecture](https://img.shields.io/badge/architecture-medallion-gold)
![Status](https://img.shields.io/badge/status-in%20progress-orange)

Practica **Activity 3 – Building a Mini Lakehouse** (Datacycle · Unidad 2 · curso 2026-27).
Pipeline de datos con arquitectura medallion: **Bronze → Silver → Gold**.

```mermaid
flowchart LR
    B[("🥉 Bronze<br/>ventas.csv<br/>clientes.json<br/>logs.txt")] -->|limpieza y normalizacion| S[("🥈 Silver<br/>clean_sales.csv<br/>clean_customers.csv<br/>clean_logs.csv")]
    S -->|agregaciones OLAP| G[("🥇 Gold<br/>sales_by_customer.csv<br/>revenue_by_product.csv")]
```

## 👥 Equipo

| Persona | Capa | Responsabilidad |
|---|---|---|
| [@Ignaciobrenas](https://github.com/Ignaciobrenas) | 🥉 Bronze | Analisis de datos crudos, estructura del repo |
| [@MauroPB30](https://github.com/MauroPB30) | 🥈 Silver | Limpieza, normalizacion, datasets limpios |
| [@gorkarmz](https://github.com/gorkarmz) | 🥇 Gold | Analitica, informe final, README |

## 📁 Estructura

```
data_lab/
├── bronze/   # datos crudos del ZIP (ventas.csv, clientes.json, logs.txt)
├── silver/   # clean_sales.csv, clean_customers.csv, clean_logs.csv
└── gold/     # sales_by_customer.csv, revenue_by_product.csv
src/          # scripts Python comentados (common, bronze_analysis, silver_clean, gold_analytics)
docs/         # informes (bronze_report, final_report) y evidencia de uso de IA (ai_usage)
```

> Nota: el enunciado en PDF nombra `sales.csv` y `customers.json`, pero el dataset entregado viene como `ventas.csv` y `clientes.json`.

## 🔗 Contrato Silver

- `clean_sales.csv`: `id_pedido,id_cliente,producto,importe`
- `clean_customers.csv`: `id_cliente,nombre,pais`
- `clean_logs.csv`: `nivel,id_cliente,action`

## 🚀 Como ejecutar

```bash
pip install -r requirements.txt
python src/bronze_analysis.py
python src/silver_clean.py
python src/gold_analytics.py
```

## 🤝 Flujo de trabajo

1. Coge un [issue](../../issues) de tu capa (etiquetas `bronze` / `silver` / `gold`).
2. Rama: `feat/<capa>-<tema>` → Pull Request a `main`, revisado por otro companero.
3. Solo edita los archivos de tu capa para evitar conflictos. Mas detalle en [PLAN.md](PLAN.md).
