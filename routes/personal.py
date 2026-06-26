from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from database.connection import execute_query
from utils.decorators import login_required, permission_required
from datetime import datetime

personal_bp = Blueprint('personal', __name__)

PER_PAGE = 10

# ──────────────────────────────────────────────
#  Datos comunes para formularios
# ──────────────────────────────────────────────
def _get_form_data():
    """Obtiene datos de tablas relacionadas para selects."""
    tipo_nomina = execute_query("SELECT * FROM TipoNomina ORDER BY 2", fetchall=True) or []
    estatus_actual = execute_query("SELECT * FROM EstatusActual ORDER BY 2", fetchall=True) or []
    tipo_contrato = execute_query("SELECT * FROM TipoContrato ORDER BY 2", fetchall=True) or []
    parroquias = execute_query("SELECT * FROM ParroquiasR ORDER BY 3", fetchall=True) or []
    cargos = execute_query("SELECT * FROM Cargos ORDER BY 2", fetchall=True) or []
    turnos = execute_query("SELECT * FROM Turnos ORDER BY 2", fetchall=True) or []
    centros_costo = execute_query("SELECT * FROM CentrosCostos ORDER BY 2", fetchall=True) or []
    return {
        'tipo_nomina': tipo_nomina,
        'estatus_actual': estatus_actual,
        'tipo_contrato': tipo_contrato,
        'parroquias': parroquias,
        'cargos': cargos,
        'turnos': turnos,
        'centros_costo': centros_costo,
    }


# ──────────────────────────────────────────────
#  Página principal (Lista)
# ──────────────────────────────────────────────
@personal_bp.route('/')
@login_required
@permission_required('personal.ver')
def index():
    return render_template('personal/index.html')


# ──────────────────────────────────────────────
#  API: Datos paginados + búsqueda
# ──────────────────────────────────────────────
@personal_bp.route('/data')
@login_required
@permission_required('personal.ver')
def get_personal_data():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    per_page = PER_PAGE

    base_query = " FROM Personal p"
    where = ""
    params = ()

    if search:
        where = """ WHERE p.Nombres LIKE ? OR p.Apellidos LIKE ? OR p.Cedula LIKE ?
                    OR p.Telefono LIKE ? OR p.Ciudad LIKE ? OR p.NumeroFicha LIKE ?"""
        s = f'%{search}%'
        params = (s, s, s, s, s, s)

    # Total
    count_row = execute_query("SELECT COUNT(*)" + base_query + where, params, fetchone=True)
    total = count_row[0] if count_row else 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Datos con JOINs a tablas relacionadas
    # NOTA: Access requiere paréntesis para múltiples LEFT JOINs
    select_query = ("SELECT p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula, p.Telefono, "
                    "p.Ciudad, p.NumeroFicha, p.FechaIngreso, "
                    "tn.Nomina AS TipoNomina, ea.EstatusA AS EstatusDesc, tc.Contrato AS ContratoDesc, "
                    "p.FK_IdTipoNomina, p.FK_IdEstatusActual, p.FK_IdTipoContrato "
                    "FROM ((Personal p "
                    "LEFT JOIN TipoNomina tn ON p.FK_IdTipoNomina = tn.IdTipoNomina) "
                    "LEFT JOIN EstatusActual ea ON p.FK_IdEstatusActual = ea.IdEstatusA) "
                    "LEFT JOIN TipoContrato tc ON p.FK_IdTipoContrato = tc.IdTipoContrato "
                    + where
                    + " ORDER BY p.IdPersonal")

    all_rows = execute_query(select_query, params, fetchall=True) or []


    # Paginar en Python
    start = (page - 1) * per_page
    end = start + per_page
    page_rows = all_rows[start:end]

    data = []
    for r in page_rows:
        data.append({
            'id': r[0],
            'nombres': r[1] or '',
            'apellidos': r[2] or '',
            'cedula': r[3] or '',
            'telefono': r[4] or '',
            'ciudad': r[5] or '',
            'num_ficha': r[6] or '',
            'fecha_ingreso': r[7].strftime('%d/%m/%Y') if r[7] else '',
            'tipo_nomina': r[8] or '',
            'estatus': r[9] or '',
            'tipo_contrato': r[10] or '',
        })

    return jsonify({
        'data': data,
        'total': total,
        'page': page,
        'total_pages': total_pages,
        'per_page': per_page,
    })


# ──────────────────────────────────────────────
#  Crear Personal (página)
# ──────────────────────────────────────────────
@personal_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@permission_required('personal.crear')
def crear():
    form_data = _get_form_data()

    if request.method == 'POST':
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        cedula = request.form.get('cedula', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        ciudad = request.form.get('ciudad', '').strip()
        fecha_ingreso = request.form.get('fecha_ingreso', '').strip()
        num_ficha = request.form.get('num_ficha', '').strip()
        id_tipo_nomina = request.form.get('id_tipo_nomina', type=int)
        id_estatus = request.form.get('id_estatus', type=int)
        id_contrato = request.form.get('id_contrato', type=int)
        id_parroquia = request.form.get('id_parroquia', type=int)
        id_cargo = request.form.get('id_cargo', type=int)
        id_turno = request.form.get('id_turno', type=int)
        id_centro_costo = request.form.get('id_centro_costo', type=int)

        if not nombres:
            flash('El campo Nombres es obligatorio.', 'danger')
            return render_template('personal/crear.html', **form_data, personal=None)

        if not apellidos:
            flash('El campo Apellidos es obligatorio.', 'danger')
            return render_template('personal/crear.html', **form_data, personal=None)

        # Convertir fecha si viene
        fecha_obj = None
        if fecha_ingreso:
            try:
                fecha_obj = datetime.strptime(fecha_ingreso, '%Y-%m-%d')
            except ValueError:
                flash('Formato de fecha inválido.', 'danger')
                return render_template('personal/crear.html', **form_data, personal=None)

        try:
            execute_query(
                """INSERT INTO Personal
                   (Nombres, Apellidos, Cedula, Telefono, Direccion, Ciudad,
                    FechaIngreso, NumeroFicha,
                    FK_IdParroquiaR, Fk_IdTipoNomina, FK_IdCargo, FK_IdTurno,
                    FK_IdEstatusActual, FK_IdTipoContrato, Fk_IdCentroCosto)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nombres, apellidos, cedula, telefono, direccion, ciudad,
                 fecha_obj, num_ficha,
                 id_parroquia, id_tipo_nomina, id_cargo, id_turno,
                 id_estatus, id_contrato, id_centro_costo),
                commit=True
            )
            flash('Personal registrado exitosamente.', 'success')
            return redirect(url_for('personal.index'))
        except Exception as e:
            flash(f'Error al registrar: {str(e)}', 'danger')

    return render_template('personal/crear.html', **form_data, personal=None)


# ──────────────────────────────────────────────
#  Editar Personal (página)
# ──────────────────────────────────────────────
@personal_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('personal.editar')
def editar(id):
    form_data = _get_form_data()

    if request.method == 'POST':
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        cedula = request.form.get('cedula', '').strip()
        telefono = request.form.get('telefono', '').strip()
        direccion = request.form.get('direccion', '').strip()
        ciudad = request.form.get('ciudad', '').strip()
        fecha_ingreso = request.form.get('fecha_ingreso', '').strip()
        num_ficha = request.form.get('num_ficha', '').strip()
        id_tipo_nomina = request.form.get('id_tipo_nomina', type=int)
        id_estatus = request.form.get('id_estatus', type=int)
        id_contrato = request.form.get('id_contrato', type=int)
        id_parroquia = request.form.get('id_parroquia', type=int)
        id_cargo = request.form.get('id_cargo', type=int)
        id_turno = request.form.get('id_turno', type=int)
        id_centro_costo = request.form.get('id_centro_costo', type=int)

        if not nombres or not apellidos:
            flash('Nombres y Apellidos son obligatorios.', 'danger')
            return redirect(url_for('personal.editar', id=id))

        fecha_obj = None
        if fecha_ingreso:
            try:
                fecha_obj = datetime.strptime(fecha_ingreso, '%Y-%m-%d')
            except ValueError:
                flash('Formato de fecha inválido.', 'danger')
                return redirect(url_for('personal.editar', id=id))

        try:
            execute_query(
                """UPDATE Personal SET
                    Nombres=?, Apellidos=?, Cedula=?, Telefono=?, Direccion=?,
                    Ciudad=?, FechaIngreso=?, NumeroFicha=?,
                    FK_IdParroquiaR=?, Fk_IdTipoNomina=?, FK_IdCargo=?, FK_IdTurno=?,
                    FK_IdEstatusActual=?, FK_IdTipoContrato=?, Fk_IdCentroCosto=?
                   WHERE IdPersonal=?""",
                (nombres, apellidos, cedula, telefono, direccion, ciudad,
                 fecha_obj, num_ficha,
                 id_parroquia, id_tipo_nomina, id_cargo, id_turno,
                 id_estatus, id_contrato, id_centro_costo,
                 id),
                commit=True
            )
            flash('Personal actualizado exitosamente.', 'success')
            return redirect(url_for('personal.index'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')

    # GET: cargar datos actuales
    row = execute_query(
        """SELECT IdPersonal, Nombres, Apellidos, Cedula, Telefono, Direccion,
                  Ciudad, FechaIngreso, NumeroFicha,
                  FK_IdParroquiaR, Fk_IdTipoNomina, FK_IdCargo, FK_IdTurno,
                  FK_IdEstatusActual, FK_IdTipoContrato, Fk_IdCentroCosto
           FROM Personal WHERE IdPersonal=?""",
        (id,), fetchone=True
    )
    if not row:
        flash('Personal no encontrado.', 'danger')
        return redirect(url_for('personal.index'))

    personal = {
        'id': row[0],
        'nombres': row[1] or '',
        'apellidos': row[2] or '',
        'cedula': row[3] or '',
        'telefono': row[4] or '',
        'direccion': row[5] or '',
        'ciudad': row[6] or '',
        'fecha_ingreso': row[7].strftime('%Y-%m-%d') if row[7] else '',
        'num_ficha': row[8] or '',
        'id_parroquia': row[9],
        'id_tipo_nomina': row[10],
        'id_cargo': row[11],
        'id_turno': row[12],
        'id_estatus': row[13],
        'id_contrato': row[14],
        'id_centro_costo': row[15],
    }

    return render_template('personal/crear.html', **form_data, personal=personal)


# ──────────────────────────────────────────────
#  Ver detalle de Personal
# ──────────────────────────────────────────────
@personal_bp.route('/<int:id>')
@login_required
@permission_required('personal.ver')
def detalle(id):
    row = execute_query(
        """SELECT p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula, p.Telefono,
                  p.Direccion, p.Ciudad, p.FechaIngreso, p.NumeroFicha,
                  tn.Nomina, ea.EstatusA, tc.Contrato,
                  pr.Parroquia, c.Cargo, t.Turno, cc.CentroCosto,
                  p.FK_IdParroquiaR, p.FK_IdTipoNomina, p.FK_IdEstatusActual,
                  p.FK_IdTipoContrato, p.FK_IdCargo, p.FK_IdTurno, p.Fk_IdCentroCosto
           FROM ((((((Personal p
           LEFT JOIN TipoNomina tn ON p.FK_IdTipoNomina = tn.IdTipoNomina)
           LEFT JOIN EstatusActual ea ON p.FK_IdEstatusActual = ea.IdEstatusA)
           LEFT JOIN TipoContrato tc ON p.FK_IdTipoContrato = tc.IdTipoContrato)
           LEFT JOIN ParroquiasR pr ON p.FK_IdParroquiaR = pr.IdParroquia)
           LEFT JOIN Cargos c ON p.FK_IdCargo = c.IdCargo)
           LEFT JOIN Turnos t ON p.FK_IdTurno = t.IdTurno)
           LEFT JOIN CentrosCostos cc ON p.Fk_IdCentroCosto = cc.IdCentroCosto
           WHERE p.IdPersonal=?""",
        (id,), fetchone=True
    )
    if not row:
        flash('Personal no encontrado.', 'danger')
        return redirect(url_for('personal.index'))

    personal = {
        'id': row[0],
        'nombres': row[1] or '',
        'apellidos': row[2] or '',
        'cedula': row[3] or '',
        'telefono': row[4] or '',
        'direccion': row[5] or '',
        'ciudad': row[6] or '',
        'fecha_ingreso': row[7].strftime('%d/%m/%Y') if row[7] else '',
        'num_ficha': row[8] or '',
        'tipo_nomina': row[9] or '',
        'estatus': row[10] or '',
        'tipo_contrato': row[11] or '',
        'parroquia': row[12] or '',
        'cargo': row[13] or '',
        'turno': row[14] or '',
        'centro_costo': row[15] or '',
    }
    return render_template('personal/detalle.html', personal=personal)


# ──────────────────────────────────────────────
#  API: Eliminar Personal (AJAX)
# ──────────────────────────────────────────────
@personal_bp.route('/<int:id>/eliminar', methods=['POST'])
@login_required
@permission_required('personal.eliminar')
def eliminar(id):
    try:
        # Verificar que no tenga usuarios asociados
        count = execute_query(
            "SELECT COUNT(*) FROM Usuarios WHERE Fk_IdPersonal=?",
            (id,), fetchone=True
        )
        if count and count[0] > 0:
            return jsonify({
                'success': False,
                'error': 'No se puede eliminar: tiene usuarios asociados.'
            })

        execute_query("DELETE FROM Personal WHERE IdPersonal=?", (id,), commit=True)
        return jsonify({'success': True, 'message': 'Personal eliminado exitosamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al eliminar: {str(e)}'})
