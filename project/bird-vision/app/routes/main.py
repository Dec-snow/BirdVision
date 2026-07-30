# -*- coding: utf-8 -*-
"""主页路由蓝图"""

from flask import Blueprint, render_template

# 创建主页蓝图
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页"""
    return render_template('index.html', active_page='home')


@main_bp.route('/detect')
def detect():
    """鸟类识别页面"""
    return render_template('detect.html', active_page='detect')


@main_bp.route('/chat')
def chat():
    """知识问答页面"""
    return render_template('chat.html', active_page='chat')


@main_bp.route('/stats')
def stats():
    """数据统计页面"""
    return render_template('stats.html', active_page='stats')


@main_bp.route('/species')
def species():
    """物种百科页面"""
    return render_template('species.html', active_page='species')