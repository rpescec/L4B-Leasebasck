from flask import Flask, request, send_file, render_template, jsonify
import os, tempfile, traceback
from gen_leaseback_v2 import generate_pdf
from generar_informe_hipotecario import generate_pdf_hipotecario

app = Flask(__name__)
BASE   = os.path.dirname(os.path.abspath(__file__))
LOGO   = os.path.join(BASE, 'logo_clean.png')
LOGO_H = os.path.join(BASE, 'logo_loans4b.png')

# ── Página principal ────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

# ── Leaseback ───────────────────────────────────────────────────────────────

@app.route('/leaseback')
def leaseback():
    return render_template('index.html')

@app.route('/simulador')
def simulador():
    return render_template('simulador.html')

@app.route('/generar_pdf', methods=['POST'])
def generar_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        generate_pdf(data, tmp_path, LOGO)
        cliente = data.get('nombre_cliente', 'cliente').replace(' ', '_')
        return send_file(tmp_path, as_attachment=True,
                         download_name=f"Reporte_Leaseback_{cliente}.pdf",
                         mimetype='application/pdf')
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ── Hipotecario ─────────────────────────────────────────────────────────────

@app.route('/hipotecario')
def hipotecario():
    return render_template('hipotecario.html')

@app.route('/generar_pdf_hipotecario', methods=['POST'])
def generar_pdf_hipotecario():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        generate_pdf_hipotecario(data, tmp_path, LOGO_H)
        cliente = data.get('nombre', 'cliente').replace(' ', '_')
        return send_file(tmp_path, as_attachment=True,
                         download_name=f"Simulacion_Hipotecaria_{cliente}.pdf",
                         mimetype='application/pdf')
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
