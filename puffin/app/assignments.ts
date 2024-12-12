import { BorbPanelBuilder } from '../borb/Frames';
import { html, render } from 'uhtml';
import { Assignment, Course, Project } from './model';
import { busy_event_handler, get_gitlab_project, request } from './puffin';
import slugify from 'slugify';
import { form_field, form_select, GITLAB_PATH_RE, GITLAB_PREFIX } from './forms';
import { pick_project_form } from './gitlab';
import { AssignmentModel_NAMES } from './model_gen';

export function slugify_to(id: string): (ev: InputEvent) => void {
    return (ev: InputEvent) => {
        const elt = document.getElementById(id);
        console.log(ev, ev.data);
        if (ev.target instanceof HTMLInputElement) {
            const newValue = slugify(ev.target.value);
            if (elt instanceof HTMLInputElement) elt.value = newValue;
            else elt.textContent = newValue;
        }
    };
}
export const assignmentCategories = ['weekly', 'compulsory', 'project', 'extra'];
export function edit_assignment_form(
    asgn: Assignment,
    editable = true,
    panel: HTMLElement = undefined,
) {
    if (!asgn) {
        asgn = new Assignment({ id: 0 }, Course.current);
        asgn.release_date = new Date();
    }
    if (!panel) panel = assignment_panel();
    const iso_date = (date: Date) => {
        if(date) {
            const pad = (i:number) => i < 10 ? "0" + i : i;
            return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`
        }
    }
    const iso_datetime = (date: Date) => {
        if(date) {
            const pad = (i:number) => i < 10 ? "0" + i : i;
            return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
        }
    }

    const edit = (ev) => {
        editable = true;
        redraw();
    };
    const cancel = busy_event_handler(
        async (ev) => {
            editable = false;
            await asgn.updateAssignment();
        },
        () => redraw(),
    );
    const save = busy_event_handler(
        async (ev) => {
            editable = false;
            const method = asgn.id ? 'PUT' : 'POST';
            if (!asgn.slug) asgn.slug = slugify(asgn.name);
            await request(
                `courses/${asgn.course.external_id}/assignments/${asgn.id || ''}`,
                method,
                {
                    name: asgn.name,
                    slug: asgn.slug,
                    release_date: iso_datetime(asgn.release_date),
                    due_date: iso_datetime(asgn.due_date),
                    grade_by_date: iso_datetime(asgn.grade_by_date),
                    assignment_model: asgn.assignment_model,
                    category: asgn.category,
                    description: asgn.description,
                    gitlab_path: asgn.gitlab_path || '',
                    gitlab_root_path: asgn.gitlab_root_path || '',
                    gitlab_test_path: asgn.gitlab_test_path || '',
                },
            );
            await asgn.updateAssignment();
        },
        () => redraw(),
    );
    const check_gitlab = (data: any) => {
        return busy_event_handler(async (ev: MouseEvent) => {
            console.log('check_gitlab', data.ref, data.field);
            if (asgn[`_${data.field}_path`] === undefined) {
                asgn[`_${data.field}_project`] = asgn[`${data.field}_project`];
                asgn[`_${data.field}_path`] = asgn[`${data.field}_project`]?.full_path() || '';
                asgn[`${data.field}_project`] = undefined;
            } else if (data.ref?.current?.value) {
                const p = await get_gitlab_project(asgn.course, data.ref.current.value);
                console.log('get_gitlab_project→', p);
                asgn[`${data.field}_project`] = p;
                asgn[`${data.field}_path`] = p.path_with_namespace
                asgn[`_${data.field}_path`] = undefined;
            } else {
                asgn[`${data.field}_project`] = undefined;
                asgn[`_${data.field}_path`] = undefined;
            }
        }, redraw);
    };
    const cancel_gitlab = (data) => {
        return busy_event_handler(async (ev: MouseEvent) => {
            console.log('cancel_gitlab', data.ref, data.field, data);
            asgn[`${data.field}_project`] = asgn[`_${data.field}_project`];
            asgn[`_${data.field}_path`] = undefined;
        }, redraw);
    };
    const change_gitlab = (ev: MouseEvent, elt: HTMLInputElement, obj: Assignment, data) => {
        console.log('change_gitlab', data.field);
        asgn[`_${data.field}_path`] = elt.value;
    };
    const change_date = (ev: Event) => {
        const elt = ev.currentTarget as HTMLInputElement;
        console.log('change date', elt.value);
        const new_date = new Date(elt.value);
        const old_date = asgn[`${elt.name}`] || new_date;
        new_date.setHours(old_date.getHours())
        new_date.setMinutes(old_date.getMinutes())
        new_date.setSeconds(old_date.getSeconds())
        asgn[`${elt.name}`] = new_date;
    };
    const redraw = () => {
        console.log('Assignment form', asgn);
        const form = html`
            ${form_field({
                editable,
                obj: asgn,
                name: 'Name',
                field: 'name',
                required: true,
            })}
            ${form_field({
                editable,
                obj: asgn,
                name: 'Description',
                field: 'description',
            })}
            ${form_select({
                editable,
                obj: asgn,
                name: 'Category',
                field: 'category',
                value: asgn.category || assignmentCategories[0],
                alternatives: assignmentCategories,
            })}
            ${form_select({
                editable,
                obj: asgn,
                name: 'Model',
                field: 'assignment_model',
                value: asgn.assignment_model || AssignmentModel_NAMES[0],
                alternatives: AssignmentModel_NAMES,
            })}
            ${form_field({
                editable: asgn._gitlab_path !== undefined,
                obj: asgn,
                pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                name: '🧑‍🏫 Main Project',
                field: 'gitlab',
                value:
                    asgn._gitlab_path !== undefined
                        ? asgn._gitlab_path
                        : asgn.gitlab_path || '',
                link_prefix: asgn._gitlab_path !== undefined ? undefined : GITLAB_PREFIX,
                onchange: change_gitlab,
                button_make_onclick: check_gitlab,
                button2_make_onclick: cancel_gitlab,
                button_title:
                    asgn._gitlab_path !== undefined ? 'Ok' : asgn.gitlab_path ? 'Change' : 'Add',
                button2_title: asgn._gitlab_path !== undefined ? 'Cancel' : undefined,
            })}
            ${form_field({
                editable: asgn._gitlab_root_path !== undefined,
                obj: asgn,
                pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                name: '🧑‍🎓 Root Project',
                field: 'gitlab_root',
                value:
                    asgn._gitlab_root_path !== undefined
                        ? asgn._gitlab_root_path
                        : asgn.gitlab_root_path || '',
                link_prefix: asgn._gitlab_root_path !== undefined ? undefined : GITLAB_PREFIX,
                onchange: change_gitlab,
                button_make_onclick: check_gitlab,
                button2_make_onclick: cancel_gitlab,
                button_title:
                    asgn._gitlab_root_path !== undefined
                        ? 'Ok'
                        : asgn.gitlab_root_path
                        ? 'Change'
                        : 'Add',
                button2_title: asgn._gitlab_root_path !== undefined ? 'Cancel' : undefined,
            })}
            ${form_field({
                editable: asgn._gitlab_test_path !== undefined,
                obj: asgn,
                pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                name: '🧪 Test Project',
                field: 'gitlab_test',
                value:
                    asgn._gitlab_test_path !== undefined
                        ? asgn._gitlab_test_path
                        : asgn.gitlab_test_path || '',
                link_prefix: asgn._gitlab_test_path !== undefined ? undefined : GITLAB_PREFIX,
                onchange: change_gitlab,
                button_make_onclick: check_gitlab,
                button2_make_onclick: cancel_gitlab,
                button_title:
                    asgn._gitlab_test_path !== undefined
                        ? 'Ok'
                        : asgn.gitlab_test_path
                        ? 'Change'
                        : 'Add',
                button2_title: asgn._gitlab_test_path !== undefined ? 'Cancel' : undefined,
            })}
            <div class="form-field">
                <label for="asgn_release_date">Release date:</label>
                <input
                    type="date"
                    id="asgn_release_date"
                    name="release_date"
                    onchange=${change_date}
                    value=${iso_date(asgn.release_date) || ''}
                />
            </div>
            <div class="form-field">
                <label for="asgn_due_date">Due date:</label>
                <input
                    type="date"
                    id="asgn_due_date"
                    name="due_date"
                    onchange=${change_date}
                    value=${iso_date(asgn.due_date) || ''}
                />
            </div>
            <div class="form-field">
                <label for="asgn_grade_date">Grade-by date:</label>
                <input
                    type="date"
                    id="asgn_grade_date"
                    name="grade_by_date"
                    onchange=${change_date}
                    value=${iso_date(asgn.grade_by_date) || ''}
                />
            </div>
            <div class="form-control">
                <button type="button" onclick=${cancel} ?disabled=${!editable}
                    >❌ Cancel Edit</button
                >
                <button type="button" onclick=${editable ? save : edit}
                    >${editable ? '💾 Save Assignment' : '🖊️ Edit Assignment'}</button
                > </div
            ><div class="log">
                ${asgn._log.map((entry) => html`<li class=${entry[0]}>${entry[1]}</li>`) || ''}</div
            >
        `;
        render(panel, form);
        return form;
    };
    return redraw();
}
function assignment_panel() {
    return new BorbPanelBuilder()
        .frame('frame2')
        .panel('form', 'edit-assignment')
        .title('New assignment')
        .select()
        .done();
}
export async function add_assignment_form(proj_ref = undefined) {
    const asgn = new Assignment({
        id: 0,
        course_id: Course.current?.external_id,
        assignment_model: AssignmentModel_NAMES[0],
    }, Course.current);
    console.log('add_assignment_form', asgn, proj_ref);
    asgn.release_date = new Date();
    asgn.release_date.setHours(23);
    asgn.release_date.setMinutes(59);
    asgn.release_date.setSeconds(59);
    asgn.release_date.setMilliseconds(0);
    const panel = assignment_panel();
    try {
        const proj_data = await pick_project_form(
            { _project_ref: proj_ref },
            'Create assignment',
            panel,
            false,
        );
        if (proj_data.gitlab_id) {
            asgn.name = proj_data.name;
            asgn.slug = proj_data.slug;
            asgn._gitlab_path = proj_data.slug;
            asgn.gitlab_project = proj_data.project;
            asgn._gitlab_root_path = proj_data.slug;
            asgn.gitlab_root_project = proj_data.project;
        }
        console.log('proj_data', proj_data);
        edit_assignment_form(asgn, true, panel);
    } catch (e) {
        console.error(e);
        panel.remove();
    }
}
