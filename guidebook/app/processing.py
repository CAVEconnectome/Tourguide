from flask import Blueprint, redirect, request, render_template, url_for, current_app
from ..base import generate_lvl2_proofreading
from .forms import Lvl2SkeletonizeForm
import numpy as np
from middle_auth_client import auth_required
import re
# from annotationframeworkclient import FrameworkClient
from rq import Queue, Retry
from rq.job import Job
from .worker import conn

api_version = 0
url_prefix = f"/guidebook"
api_prefix = f"/api/v{api_version}"

bp = Blueprint("guidebook", __name__, url_prefix=url_prefix)
__version__ = "0.0.2"

q = Queue(connection=conn)


@bp.route("/version")
def version_text():
    return f"Neuron Guidebook v.{__version__}"


@bp.route("/")
# @auth_required
def landing_page():
    return render_template('landing.html',
                           title=f'Neuron Guidebook',
                           datastack=current_app.config.get("DATASTACK"),
                           version=__version__,
                           )


def encode_root_location(form_data):
    if len(form_data) == 0:
        return None
    elif re.match(r"^( |\d)*,( |\d)*,( |\d)*$", form_data):
        root_loc_data = np.fromstring(
            form_data, count=3, dtype=np.int, sep=',')
        root_loc_formatted = '_'.join(map(str, root_loc_data))
        return root_loc_formatted
    else:
        raise ValueError(
            "Root location must be specified with 3 comma-separated numbers")


def parse_root_location(root_loc):
    if root_loc is not None:
        root_loc = np.array(root_loc.split('_')).astype(
            int)
        print(f'Root location is: {root_loc}')
    return root_loc


@bp.route(f"{api_prefix}/datastack/<datastack>/root_id/<int:root_id>/l2skeleton")
# @auth_required
def generate_guidebook_chunkgraph(datastack, root_id):
    root_loc = parse_root_location(request.args.get('root_location', None))
    branch_points = request.args.get('branch_points', 'True') == 'True'
    end_points = request.args.get('end_points', 'True') == 'True'
    collapse_soma = request.args.get('collapse_soma') == 'True'
    segmentation_fallback = request.args.get(
        'segmentation_fallback', False) == 'True'
    kwargs = {
        'return_as': 'url',
        'root_point': root_loc,
        'refine_branch_points': branch_points,
        'refine_end_points': end_points,
        'collapse_soma': collapse_soma,
        'n_parallel': int(current_app.config.get('N_PARALLEL')),
        'segmentation_fallback': segmentation_fallback,
    }
    print(kwargs)
    job = q.enqueue_call(generate_lvl2_proofreading,
                         args=(datastack, int(root_id)),
                         kwargs=kwargs,
                         result_ttl=5000,
                         timeout=600,
                         retry=Retry(max=2, interval=10))
    return redirect(url_for('.show_skeletonization_result', job_key=job.get_id()))


@bp.route('/skeletonization/results/<job_key>')
# @auth_required
def show_skeletonization_result(job_key):
    job = Job.fetch(job_key, connection=conn)
    if job.is_finished:
        return render_template('show_link.html', ngl_url=job.result, version=__version__)
    elif job.get_status() == "failed":
        return error_page(job.exc_info)
    else:
        return wait_page(10)


def error_page(error):
    return render_template("error.html",
                           error_text=error,
                           version=__version__)


def wait_page(reload_time):
    return render_template("job_wait.html",
                           reload_time=reload_time,
                           version=__version__)


@bp.route("skeletonize", methods=['GET', 'POST'])
# @auth_required
def lvl2_form():
    form = Lvl2SkeletonizeForm()
    if form.validate_on_submit():
        datastack = current_app.config.get('DATASTACK')
        root_id = form.root_id.data
        point_option = form.point_option.data
        segmentation_fallback = form.segmentation_fallback.data
        if point_option == 'both':
            branch_points = True
            end_points = True
        elif point_option == 'ep':
            branch_points = False
            end_points = True
        elif point_option == 'bp':
            branch_points = True
            end_points = False
        try:
            root_loc_formatted = encode_root_location(form.root_location.data)
        except Exception as e:
            return error_page(e)
        root_is_soma = form.root_is_soma.data
        url = url_for('.generate_guidebook_chunkgraph',
                      datastack=datastack,
                      root_id=root_id,
                      root_location=root_loc_formatted,
                      branch_points=branch_points,
                      end_points=end_points,
                      collapse_soma=root_is_soma,
                      segmentation_fallback=segmentation_fallback)
        return redirect(url)

    return render_template('lvl2_skeletonize.html',
                           title='Neuron Guidebook',
                           form=form,
                           version=__version__,
                           allow_segmentation=current_app.config.get('ALLOW_SEGMENTATION', False))
