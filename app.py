import os
from datetime import date
from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, send_file)
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, IntegerField, DateField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Email, NumberRange
from sqlalchemy import create_engine, or_, desc, asc
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy import BigInteger, String, Integer, Date, CHAR
from dotenv import load_dotenv
import csv
import io

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
csrf = CSRFProtect(app)

DATABASE_URL = os.getenv('DATABASE_URL')
PAGE_SIZE = int(os.getenv('PAGE_SIZE', '10'))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não foi definido. Configure a variável de ambiente.")

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)

class Base(DeclarativeBase):
    pass

class Cliente(Base):
    __tablename__ = 'clientes'
    __table_args__ = {"schema": 'N8N'}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nome: Mapped[str] = mapped_column(String(50))
    celzap: Mapped[str] = mapped_column(String(15))
    empresa: Mapped[str] = mapped_column(String(50))
    contrato: Mapped[str] = mapped_column(String(15))
    disparos: Mapped[int] = mapped_column(Integer, default=0)
    ultdisparo: Mapped[date | None] = mapped_column(Date, nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cpfresp: Mapped[str | None] = mapped_column(String(15), nullable=True)
    dtatend1: Mapped[date | None] = mapped_column(Date, nullable=True)
    dtatend2: Mapped[date | None] = mapped_column(Date, nullable=True)
    dtatend3: Mapped[date | None] = mapped_column(Date, nullable=True)
    dtatend4: Mapped[date | None] = mapped_column(Date, nullable=True)
    finalstatus: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    email: Mapped[str | None] = mapped_column(String(25), nullable=True)
    emailcontato: Mapped[str | None] = mapped_column(String(100), nullable=True)

class ClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=50)])
    celzap = StringField('Cel/WhatsApp', validators=[DataRequired(), Length(max=15)])
    empresa = StringField('Empresa', validators=[DataRequired(), Length(max=50)])
    contrato = StringField('Contrato', validators=[DataRequired(), Length(max=15)])
    disparos = IntegerField('Disparos', validators=[Optional(), NumberRange(min=0)])
    ultdisparo = DateField('Último Disparo', validators=[Optional()])
    cnpj = StringField('CNPJ', validators=[Optional(), Length(max=20)])
    cpfresp = StringField('CPF Responsável', validators=[Optional(), Length(max=15)])
    dtatend1 = DateField('Atendimento 1', validators=[Optional()])
    dtatend2 = DateField('Atendimento 2', validators=[Optional()])
    dtatend3 = DateField('Atendimento 3', validators=[Optional()])
    dtatend4 = DateField('Atendimento 4', validators=[Optional()])
    finalstatus = SelectField('Status Final', choices=[('', '—'), ('A', 'Ativo'), ('I', 'Inativo'), ('C', 'Cancelado')], validators=[Optional()])
    email = StringField('E-mail', validators=[Optional(), Email(), Length(max=25)])
    emailcontato = StringField('E-mail de Contato', validators=[Optional(), Email(), Length(max=100)])

def _pagination(query, page, page_size):
    total = query.count()
    items = query.offset((page-1)*page_size).limit(page_size).all()
    return total, items

@app.route('/')
def home():
    return redirect(url_for('clientes_list'))

@app.route('/clientes')
def clientes_list():
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'desc')
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', PAGE_SIZE))

    with Session(engine) as session:
        query = session.query(Cliente)
        if q:
            like = f"%{q}%"
            query = query.filter(or_(
                Cliente.nome.ilike(like),
                Cliente.empresa.ilike(like),
                Cliente.cnpj.ilike(like),
                Cliente.cpfresp.ilike(like),
                Cliente.celzap.ilike(like),
                Cliente.email.ilike(like)
            ))
        col = getattr(Cliente, sort if hasattr(Cliente, sort) else 'id')
        query = query.order_by(desc(col) if order == 'desc' else asc(col))

        total, clientes = _pagination(query, page, page_size)

    return render_template('clientes_list.html',
                           clientes=clientes,
                           total=total,
                           q=q, sort=sort, order=order,
                           page=page, page_size=page_size)

@app.route('/clientes/<int:cid>')
def clientes_get(cid: int):
    with Session(engine) as session:
        c = session.get(Cliente, cid)
        if not c:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'id': c.id,
            'nome': c.nome,
            'celzap': c.celzap,
            'empresa': c.empresa,
            'contrato': c.contrato,
            'disparos': c.disparos,
            'ultdisparo': c.ultdisparo.isoformat() if c.ultdisparo else '',
            'cnpj': c.cnpj or '',
            'cpfresp': c.cpfresp or '',
            'dtatend1': c.dtatend1.isoformat() if c.dtatend1 else '',
            'dtatend2': c.dtatend2.isoformat() if c.dtatend2 else '',
            'dtatend3': c.dtatend3.isoformat() if c.dtatend3 else '',
            'dtatend4': c.dtatend4.isoformat() if c.dtatend4 else '',
            'finalstatus': c.finalstatus or '',
            'email': c.email or '',
            'emailcontato': c.emailcontato or ''
        })

@app.route('/clientes/create', methods=['POST'])
def clientes_create():
    form = ClienteForm()
    if form.validate_on_submit():
        with Session(engine) as session:
            c = Cliente(
                nome=form.nome.data,
                celzap=form.celzap.data,
                empresa=form.empresa.data,
                contrato=form.contrato.data,
                disparos=form.disparos.data or 0,
                ultdisparo=form.ultdisparo.data,
                cnpj=form.cnpj.data or None,
                cpfresp=form.cpfresp.data or None,
                dtatend1=form.dtatend1.data,
                dtatend2=form.dtatend2.data,
                dtatend3=form.dtatend3.data,
                dtatend4=form.dtatend4.data,
                finalstatus=form.finalstatus.data or None,
                email=form.email.data or None,
                emailcontato=form.emailcontato.data or None,
            )
            session.add(c)
            session.commit()
            flash('Cliente criado com sucesso!', 'success')
    else:
        flash('Erro de validação. Verifique os campos.', 'danger')
    return redirect(url_for('clientes_list', **request.args))

@app.route('/clientes/<int:cid>/update', methods=['POST'])
def clientes_update(cid: int):
    form = ClienteForm()
    if form.validate_on_submit():
        with Session(engine) as session:
            c = session.get(Cliente, cid)
            if not c:
                flash('Registro não encontrado.', 'warning')
            else:
                c.nome = form.nome.data
                c.celzap = form.celzap.data
                c.empresa = form.empresa.data
                c.contrato = form.contrato.data
                c.disparos = form.disparos.data or 0
                c.ultdisparo = form.ultdisparo.data
                c.cnpj = form.cnpj.data or None
                c.cpfresp = form.cpfresp.data or None
                c.dtatend1 = form.dtatend1.data
                c.dtatend2 = form.dtatend2.data
                c.dtatend3 = form.dtatend3.data
                c.dtatend4 = form.dtatend4.data
                c.finalstatus = form.finalstatus.data or None
                c.email = form.email.data or None
                c.emailcontato = form.emailcontato.data or None
                session.commit()
                flash('Cliente atualizado!', 'success')
    else:
        flash('Erro de validação. Verifique os campos.', 'danger')
    return redirect(url_for('clientes_list', **request.args))

@app.route('/clientes/<int:cid>/delete', methods=['POST'])
def clientes_delete(cid: int):
    with Session(engine) as session:
        c = session.get(Cliente, cid)
        if not c:
            flash('Registro não encontrado.', 'warning')
        else:
            session.delete(c)
            session.commit()
            flash('Cliente removido.', 'success')
    return redirect(url_for('clientes_list', **request.args))

@app.route('/clientes/export.csv')
def clientes_export():
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'id')
    order = request.args.get('order', 'desc')

    with Session(engine) as session:
        query = session.query(Cliente)
        if q:
            like = f"%{q}%"
            query = query.filter(or_(
                Cliente.nome.ilike(like),
                Cliente.empresa.ilike(like),
                Cliente.cnpj.ilike(like),
                Cliente.cpfresp.ilike(like),
                Cliente.celzap.ilike(like),
                Cliente.email.ilike(like)
            ))
        col = getattr(Cliente, sort if hasattr(Cliente, sort) else 'id')
        query = query.order_by(desc(col) if order == 'desc' else asc(col))
        rows = query.all()

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['id','nome','celzap','empresa','contrato','disparos','ultdisparo','cnpj','cpfresp','dtatend1','dtatend2','dtatend3','dtatend4','finalstatus','email','emailcontato'])
    for c in rows:
        writer.writerow([
            c.id, c.nome, c.celzap, c.empresa, c.contrato, c.disparos,
            c.ultdisparo, c.cnpj, c.cpfresp, c.dtatend1, c.dtatend2,
            c.dtatend3, c.dtatend4, c.finalstatus, c.email, c.emailcontato
        ])
    mem = io.BytesIO(out.getvalue().encode('utf-8'))
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='clientes.csv')

if __name__ == '__main__':
    app.run(debug=True, port=5080)
