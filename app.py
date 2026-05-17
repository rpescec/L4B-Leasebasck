from flask import Flask, request, send_file, render_template, jsonify
import json, os, tempfile, traceback
from gen_leaseback_v2 import generate_pdf
from counter import get_next

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(BASE, 'logo_clean.png')

@app.route('/')
def index():
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

        # Asignar número correlativo
        num = get_next()
        data['numero_simulacion'] = num

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp_path = tmp.name
        generate_pdf(data, tmp_path, LOGO)

        cliente = data.get('nombre_cliente', 'cliente').replace(' ', '_')
        nombre_archivo = f"SIM-{num:04d}_Leaseback_{cliente}.pdf"
        return send_file(tmp_path, as_attachment=True,
                         download_name=nombre_archivo,
                         mimetype='application/pdf')
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
