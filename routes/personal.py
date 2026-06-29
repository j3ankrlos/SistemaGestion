from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import current_user
from database.connection import execute_query, get_connection
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
    estados = execute_query("SELECT * FROM EstadosR ORDER BY 2", fetchall=True) or []
    cargos = execute_query("SELECT * FROM Cargos ORDER BY 2", fetchall=True) or []
    turnos = execute_query("SELECT * FROM Turnos ORDER BY 2", fetchall=True) or []
    centros_costo = execute_query("SELECT * FROM CentrosCostos ORDER BY 2", fetchall=True) or []
    # Áreas: filtrar por sitio si no es SuperAdmin
    is_admin = current_user.rol_id == 1
    user_sitio = current_user.fk_sitio
    if is_admin or not user_sitio:
        areas = execute_query("SELECT IdArea, Area FROM Areas ORDER BY Area", fetchall=True) or []
    else:
        areas = execute_query("SELECT IdArea, Area FROM Areas WHERE Fk_IdSitio = ? ORDER BY Area", (user_sitio,), fetchall=True) or []
    return {
        'tipo_nomina': tipo_nomina,
        'estatus_actual': estatus_actual,
        'tipo_contrato': tipo_contrato,
        'estados': estados,
        'cargos': cargos,
        'turnos': turnos,
        'centros_costo': centros_costo,
        'areas': areas,
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

    is_admin = current_user.rol_id == 1
    user_sitio = current_user.fk_sitio

    base_query = " FROM Personal p"
    where_conditions = []
    params = []

    # Si no es SuperAdmin, filtrar por sitio vía subconsulta a CentrosCostos
    if not is_admin and user_sitio:
        where_conditions.append("p.Fk_IdCentroCosto IN (SELECT IdCentroCosto FROM CentrosCostos WHERE Fk_IdSitio = ?)")
        params.append(user_sitio)

    if search:
        where_conditions.append("""(p.Nombres LIKE ? OR p.Apellidos LIKE ? OR p.Cedula LIKE ?
                    OR p.NumeroFicha LIKE ?)""")
        s = f'%{search}%'
        params.extend([s, s, s, s])

    where = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    params = tuple(params) if params else ()

    # Total
    count_row = execute_query("SELECT COUNT(*)" + base_query + where, params, fetchone=True)
    total = count_row[0] if count_row else 0
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Datos con JOINs a tablas relacionadas
    # NOTA: Access requiere paréntesis para múltiples LEFT JOINs
    select_query = ("SELECT p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula, "
                    "p.NumeroFicha, p.FechaIngreso, "
                    "tn.Nomina AS TipoNomina, ea.EstatusA AS EstatusDesc, tc.Contrato AS ContratoDesc, "
                    "p.FK_IdTipoNomina, p.FK_IdEstatusActual, p.FK_IdTipoContrato, "
                    "a.Area AS AreaTrabajo "
                    "FROM (((Personal p "
                    "LEFT JOIN TipoNomina tn ON p.FK_IdTipoNomina = tn.IdTipoNomina) "
                    "LEFT JOIN EstatusActual ea ON p.FK_IdEstatusActual = ea.IdEstatusA) "
                    "LEFT JOIN TipoContrato tc ON p.FK_IdTipoContrato = tc.IdTipoContrato) "
                    "LEFT JOIN Areas a ON p.Fk_Area = a.IdArea "
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
            'telefono': '',  # ahora está en Direcciones, se muestra en detalle
            'num_ficha': r[4] or '',
            'fecha_ingreso': r[5].strftime('%d/%m/%Y') if r[5] else '',
            'tipo_nomina': r[6] or '',
            'estatus': r[7] or '',
            'tipo_contrato': r[8] or '',
            'area': r[12] or '',
        })

    return jsonify({
        'data': data,
        'total': total,
        'page': page,
        'total_pages': total_pages,
        'per_page': per_page,
    })


# ──────────────────────────────────────────────
#  API: Municipios por Estado (combos anidados)
# ──────────────────────────────────────────────
@personal_bp.route('/api/municipios/<int:estado_id>')
@login_required
def api_municipios(estado_id):
    rows = execute_query(
        "SELECT IdMunicipio, Municipio FROM MunicipiosR WHERE FK_IdEstado=? ORDER BY 2",
        (estado_id,), fetchall=True
    ) or []
    return jsonify([{'id': r[0], 'nombre': r[1]} for r in rows])


# ──────────────────────────────────────────────
#  API: Parroquias por Municipio (combos anidados)
# ──────────────────────────────────────────────
@personal_bp.route('/api/parroquias/<int:municipio_id>')
@login_required
def api_parroquias(municipio_id):
    rows = execute_query(
        "SELECT IdParroquia, Parroquia FROM ParroquiasR WHERE FK_IdMunicipio=? ORDER BY 2",
        (municipio_id,), fetchall=True
    ) or []
    return jsonify([{'id': r[0], 'nombre': r[1]} for r in rows])


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
        fecha_ingreso = request.form.get('fecha_ingreso', '').strip()
        num_ficha = request.form.get('num_ficha', '').strip()
        id_tipo_nomina = request.form.get('id_tipo_nomina', type=int)
        id_estatus = request.form.get('id_estatus', type=int)
        id_contrato = request.form.get('id_contrato', type=int)
        id_parroquia = request.form.get('id_parroquia', type=int)
        id_cargo = request.form.get('id_cargo', type=int)
        id_turno = request.form.get('id_turno', type=int)
        id_centro_costo = request.form.get('id_centro_costo', type=int)
        id_area = request.form.get('id_area', type=int)

        # Datos de Direcciones
        telefono_fijo = request.form.get('telefono_fijo', '').strip()
        telefono_movil = request.form.get('telefono_movil', '').strip()
        direccion = request.form.get('direccion', '').strip()
        ciudad = request.form.get('ciudad', '').strip()
        id_estado = request.form.get('id_estado', type=int)
        id_municipio = request.form.get('id_municipio', type=int)
        id_parroquia_dir = request.form.get('id_parroquia', type=int)

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
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO Personal
                   (Nombres, Apellidos, Cedula,
                    FechaIngreso, NumeroFicha,
                    FK_IdParroquiaR, Fk_IdTipoNomina, FK_IdCargo, FK_IdTurno,
                    FK_IdEstatusActual, FK_IdTipoContrato, Fk_IdCentroCosto,
                    Fk_Area, FechaRegistro, Fk_IdUsuario)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (nombres, apellidos, cedula,
                 fecha_obj, num_ficha,
                 id_parroquia_dir, id_tipo_nomina, id_cargo, id_turno,
                 id_estatus, id_contrato, id_centro_costo,
                 id_area, datetime.now(), current_user.id)
            )
            conn.commit()

            # Obtener el ID recién insertado
            cursor.execute("SELECT @@IDENTITY")
            new_id = cursor.fetchone()[0]

            # Insertar dirección en tabla Direcciones
            cursor.execute(
                """INSERT INTO Direcciones
                   (Fk_IdPersonal, Fk_IdEstado, Fk_IdMunicipio, Fk_IdParroquia,
                    Ciudad, Direccion, TelefonoFijo, TelefonoMovil)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_id, id_estado, id_municipio, id_parroquia_dir,
                 ciudad, direccion, telefono_fijo, telefono_movil)
            )
            conn.commit()

            # Si es Médico Veterinario (ID=4), insertar detalles médicos
            if id_cargo == 4:
                colegio = request.form.get('colegio_medicos', '').strip()
                estado_med = request.form.get('estado_medico', '').strip()
                codigo_mpps = request.form.get('codigo_mpps', '').strip()
                area = request.form.get('area_produccion', '').strip()
                unidad = request.form.get('unidad_medico', '').strip()
                siglas = request.form.get('siglas_medico', '').strip()

                cursor.execute(
                    """INSERT INTO DetallesMedicos
                       (FK_IdPersonal, ColegioMedicos, Estado, CodigoMPPS,
                        AreaProduccion, Unidad, Siglas)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (new_id, colegio, estado_med, codigo_mpps, area, unidad, siglas)
                )
                conn.commit()

            conn.close()
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
        fecha_ingreso = request.form.get('fecha_ingreso', '').strip()
        num_ficha = request.form.get('num_ficha', '').strip()
        id_tipo_nomina = request.form.get('id_tipo_nomina', type=int)
        id_estatus = request.form.get('id_estatus', type=int)
        id_contrato = request.form.get('id_contrato', type=int)
        id_parroquia = request.form.get('id_parroquia', type=int)
        id_cargo = request.form.get('id_cargo', type=int)
        id_turno = request.form.get('id_turno', type=int)
        id_centro_costo = request.form.get('id_centro_costo', type=int)
        id_area = request.form.get('id_area', type=int)

        # Datos de Direcciones
        telefono_fijo = request.form.get('telefono_fijo', '').strip()
        telefono_movil = request.form.get('telefono_movil', '').strip()
        direccion = request.form.get('direccion', '').strip()
        ciudad = request.form.get('ciudad', '').strip()
        id_estado = request.form.get('id_estado', type=int)
        id_municipio = request.form.get('id_municipio', type=int)
        id_parroquia_dir = request.form.get('id_parroquia', type=int)

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
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE Personal SET
                    Nombres=?, Apellidos=?, Cedula=?,
                    FechaIngreso=?, NumeroFicha=?,
                    FK_IdParroquiaR=?, Fk_IdTipoNomina=?, FK_IdCargo=?, FK_IdTurno=?,
                    FK_IdEstatusActual=?, FK_IdTipoContrato=?, Fk_IdCentroCosto=?,
                    Fk_Area=?
                   WHERE IdPersonal=?""",
                (nombres, apellidos, cedula,
                 fecha_obj, num_ficha,
                 id_parroquia_dir, id_tipo_nomina, id_cargo, id_turno,
                 id_estatus, id_contrato, id_centro_costo,
                 id_area,
                 id)
            )
            conn.commit()

            # Upsert Direcciones
            cursor.execute(
                "SELECT IdDireccion FROM Direcciones WHERE Fk_IdPersonal=?",
                (id,)
            )
            existing_dir = cursor.fetchone()
            if existing_dir:
                cursor.execute(
                    """UPDATE Direcciones SET
                        Fk_IdEstado=?, Fk_IdMunicipio=?, Fk_IdParroquia=?,
                        Ciudad=?, Direccion=?, TelefonoFijo=?, TelefonoMovil=?
                       WHERE Fk_IdPersonal=?""",
                    (id_estado, id_municipio, id_parroquia_dir,
                     ciudad, direccion, telefono_fijo, telefono_movil, id)
                )
            else:
                cursor.execute(
                    """INSERT INTO Direcciones
                       (Fk_IdPersonal, Fk_IdEstado, Fk_IdMunicipio, Fk_IdParroquia,
                        Ciudad, Direccion, TelefonoFijo, TelefonoMovil)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (id, id_estado, id_municipio, id_parroquia_dir,
                     ciudad, direccion, telefono_fijo, telefono_movil)
                )
            conn.commit()

            # Manejar DetallesMedicos según el cargo
            colegio = request.form.get('colegio_medicos', '').strip()
            estado_med = request.form.get('estado_medico', '').strip()
            codigo_mpps = request.form.get('codigo_mpps', '').strip()
            area = request.form.get('area_produccion', '').strip()
            unidad = request.form.get('unidad_medico', '').strip()
            siglas = request.form.get('siglas_medico', '').strip()

            if id_cargo == 4:
                # Verificar si ya existe registro médico
                cursor.execute(
                    "SELECT IdDetalleMedico FROM DetallesMedicos WHERE FK_IdPersonal=?",
                    (id,)
                )
                existing = cursor.fetchone()
                if existing:
                    cursor.execute(
                        """UPDATE DetallesMedicos SET
                            ColegioMedicos=?, Estado=?, CodigoMPPS=?,
                            AreaProduccion=?, Unidad=?, Siglas=?
                           WHERE FK_IdPersonal=?""",
                        (colegio, estado_med, codigo_mpps, area, unidad, siglas, id)
                    )
                else:
                    cursor.execute(
                        """INSERT INTO DetallesMedicos
                           (FK_IdPersonal, ColegioMedicos, Estado, CodigoMPPS,
                            AreaProduccion, Unidad, Siglas)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (id, colegio, estado_med, codigo_mpps, area, unidad, siglas)
                    )
            else:
                # Si cambió a otro cargo, eliminar datos médicos
                cursor.execute(
                    "DELETE FROM DetallesMedicos WHERE FK_IdPersonal=?",
                    (id,)
                )
            conn.commit()
            conn.close()

            flash('Personal actualizado exitosamente.', 'success')
            return redirect(url_for('personal.index'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')

    # GET: cargar datos actuales con LEFT JOIN a Direcciones
    row = execute_query(
        """SELECT p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula,
                  p.FechaIngreso, p.NumeroFicha,
                  d.TelefonoFijo, d.TelefonoMovil, d.Direccion, d.Ciudad,
                  d.Fk_IdEstado, d.Fk_IdMunicipio, d.Fk_IdParroquia,
                  p.FK_IdParroquiaR, p.Fk_IdTipoNomina, p.FK_IdCargo, p.FK_IdTurno,
                  p.FK_IdEstatusActual, p.FK_IdTipoContrato, p.Fk_IdCentroCosto,
                  p.Fk_Area
           FROM Personal p LEFT JOIN Direcciones d ON p.IdPersonal = d.Fk_IdPersonal
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
        'fecha_ingreso': row[4].strftime('%Y-%m-%d') if row[4] else '',
        'num_ficha': row[5] or '',
        'telefono_fijo': row[6] or '',
        'telefono_movil': row[7] or '',
        'direccion': row[8] or '',
        'ciudad': row[9] or '',
        'id_estado': row[10],
        'id_municipio': row[11],
        'id_parroquia': row[12] or row[13],  # Fk_IdParroquia de Direcciones, fallback a FK_IdParroquiaR
        'id_tipo_nomina': row[14],
        'id_cargo': row[15],
        'id_turno': row[16],
        'id_estatus': row[17],
        'id_contrato': row[18],
        'id_centro_costo': row[19],
        'id_area': row[20],
    }

    # Cargar datos médicos si existe
    med = execute_query(
        "SELECT ColegioMedicos, Estado, CodigoMPPS, AreaProduccion, Unidad, Siglas FROM DetallesMedicos WHERE FK_IdPersonal=?",
        (id,), fetchone=True
    )
    if med:
        personal['medico'] = {
            'colegio': med[0] or '',
            'estado': med[1] or '',
            'codigo_mpps': med[2] or '',
            'area_produccion': med[3] or '',
            'unidad': med[4] or '',
            'siglas': med[5] or '',
        }

    return render_template('personal/crear.html', **form_data, personal=personal)


# ──────────────────────────────────────────────
#  Ver detalle de Personal
# ──────────────────────────────────────────────
@personal_bp.route('/<int:id>')
@login_required
@permission_required('personal.ver')
def detalle(id):
    # Primera consulta: datos personales + laborales
    row = execute_query(
        """SELECT p.IdPersonal, p.Nombres, p.Apellidos, p.Cedula,
                  p.FechaIngreso, p.NumeroFicha,
                  tn.Nomina, ea.EstatusA, tc.Contrato,
                  c.Cargo, t.Turno, cc.CentroCosto,
                  p.FK_IdCargo, p.FK_IdTipoNomina, p.FK_IdEstatusActual,
                  p.FK_IdTipoContrato, p.FK_IdTurno, p.Fk_IdCentroCosto,
                  a.Area
           FROM (((((((Personal p
           LEFT JOIN TipoNomina tn ON p.FK_IdTipoNomina = tn.IdTipoNomina)
           LEFT JOIN EstatusActual ea ON p.FK_IdEstatusActual = ea.IdEstatusA)
           LEFT JOIN TipoContrato tc ON p.FK_IdTipoContrato = tc.IdTipoContrato)
           LEFT JOIN Cargos c ON p.FK_IdCargo = c.IdCargo)
           LEFT JOIN Turnos t ON p.FK_IdTurno = t.IdTurno)
           LEFT JOIN CentrosCostos cc ON p.Fk_IdCentroCosto = cc.IdCentroCosto)
           LEFT JOIN Areas a ON p.Fk_Area = a.IdArea)
           WHERE p.IdPersonal=?""",
        (id,), fetchone=True
    )
    if not row:
        flash('Personal no encontrado.', 'danger')
        return redirect(url_for('personal.index'))

    # Segunda consulta: datos de dirección con geografía
    dir_row = execute_query(
        """SELECT d.TelefonoFijo, d.TelefonoMovil, d.Direccion, d.Ciudad,
                  pr.Parroquia, mr.Municipio, er.Estado
           FROM (((Direcciones d
           LEFT JOIN ParroquiasR pr ON d.Fk_IdParroquia = pr.IdParroquia)
           LEFT JOIN MunicipiosR mr ON d.Fk_IdMunicipio = mr.IdMunicipio)
           LEFT JOIN EstadosR er ON d.Fk_IdEstado = er.IdEstado)
           WHERE d.Fk_IdPersonal=?""",
        (id,), fetchone=True
    )

    personal = {
        'id': row[0],
        'nombres': row[1] or '',
        'apellidos': row[2] or '',
        'cedula': row[3] or '',
        'fecha_ingreso': row[4].strftime('%d/%m/%Y') if row[4] else '',
        'num_ficha': row[5] or '',
        'tipo_nomina': row[6] or '',
        'estatus': row[7] or '',
        'tipo_contrato': row[8] or '',
        'cargo': row[9] or '',
        'turno': row[10] or '',
        'centro_costo': row[11] or '',
        'area': row[18] or '',
        'id_cargo': row[12],
        'telefono_fijo': dir_row[0] or '' if dir_row else '',
        'telefono_movil': dir_row[1] or '' if dir_row else '',
        'telefono': dir_row[1] or '' if dir_row else '',  # móvil como principal
        'direccion': dir_row[2] or '' if dir_row else '',
        'ciudad': dir_row[3] or '' if dir_row else '',
        'parroquia': dir_row[4] or '' if dir_row else '',
        'municipio': dir_row[5] or '' if dir_row else '',
        'estado': dir_row[6] or '' if dir_row else '',
    }

    # Cargar datos médicos si existe
    med = execute_query(
        "SELECT ColegioMedicos, Estado, CodigoMPPS, AreaProduccion, Unidad, Siglas FROM DetallesMedicos WHERE FK_IdPersonal=?",
        (id,), fetchone=True
    )
    if med:
        personal['medico'] = {
            'colegio': med[0] or '',
            'estado': med[1] or '',
            'codigo_mpps': med[2] or '',
            'area_produccion': med[3] or '',
            'unidad': med[4] or '',
            'siglas': med[5] or '',
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

        # Eliminar registros relacionados
        execute_query("DELETE FROM Direcciones WHERE Fk_IdPersonal=?", (id,), commit=True)
        execute_query("DELETE FROM DetallesMedicos WHERE FK_IdPersonal=?", (id,), commit=True)
        execute_query("DELETE FROM Personal WHERE IdPersonal=?", (id,), commit=True)
        return jsonify({'success': True, 'message': 'Personal eliminado exitosamente.'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al eliminar: {str(e)}'})
