import { BorbPanelBuilder } from '../borb/Frames';
import { html, render } from 'uhtml';
import { Assignment, Course, Project } from './model';
import { busy_event_handler, get_gitlab_project, request } from './puffin';
import slugify from 'slugify';
import { form_field, form_select, GITLAB_PATH_RE, GITLAB_PREFIX } from './forms';

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
        asgn = new Assignment({ id: 0 });
        asgn.release_date = new Date();
        asgn.course = Course.current;
    }
    if (!panel) panel = assignment_panel();
    const edit = (ev) => {
        editable = true;
        redraw();
    };
    const cancel = busy_event_handler(async (ev) => {
        editable = false;
        await asgn.updateAssignment();
    }, () => redraw());
    const save = busy_event_handler(async (ev) => {
        editable = false;
        await request(`courses/${asgn.course.external_id}/assignments/${asgn.id}`, 'PUT', {
            name: asgn.name,
            slug: asgn.slug,
            release_date: asgn.release_date,
            due_date: asgn.due_date,
            grade_by_date: asgn.grade_by_date,
            assignment_model: asgn.assignment_model,
            category: asgn.category,
            description:asgn.description,
            gitlab_id: asgn.gitlab_project?.id,
            gitlab_root_id: asgn.gitlab_root_project?.id,
            gitlab_test_id: asgn.gitlab_test_project?.id,
        });
        await asgn.updateAssignment();
    }, () => redraw());
        const check_gitlab = (data:any) => {
        return busy_event_handler(
            async (ev: MouseEvent) => {
                console.log('check_gitlab', data.ref, data.field);
                if (asgn[`_${data.field}_path`] === undefined) {
                    asgn[`_${data.field}_project`] = asgn[`${data.field}_project`];
                    asgn[`_${data.field}_path`] = asgn[`${data.field}_project`]?.full_path() || '';
                    asgn[`${data.field}_project`] = undefined;
                } else if (data.ref?.current?.value) {
                    const p = await get_gitlab_project(asgn.course, data.ref.current.value);
                    console.log('get_gitlab_project→', p);
                    asgn[`${data.field}_project`] = new Project(p);
                    asgn[`_${data.field}_path`] = undefined;
                } else {
                    asgn[`${data.field}_project`] = undefined;
                    asgn[`_${data.field}_path`] = undefined;
                }
            },
            redraw,
        );
    };
    const cancel_gitlab = (data) => {
        return busy_event_handler(
            async (ev: MouseEvent) => {
                console.log('cancel_gitlab', data.ref, data.field,data);
                asgn[`${data.field}_project`] = asgn[`_${data.field}_project`];
                asgn[`_${data.field}_path`] = undefined;
            },
            redraw,
        );
    };
    const change_gitlab = (ev:MouseEvent, elt:HTMLInputElement, obj:Assignment, data) => {
        console.log('change_gitlab', data.field);
        asgn[`_${data.field}_path`] = elt.value;
    }
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
                alternatives: assignmentCategories,
            })}
            ${form_field({
                editable: asgn._gitlab_path !== undefined,
                obj: asgn,
                pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                name: '🧑‍🏫 Main Project',
                field: 'gitlab',
                value: asgn._gitlab_path !== undefined ? asgn._gitlab_path : asgn.gitlab_project?.name||'',
                link_prefix: asgn._gitlab_path !== undefined ? undefined : GITLAB_PREFIX,
                onchange: change_gitlab,
                button_make_onclick: check_gitlab,
                button2_make_onclick: cancel_gitlab,
                button_title: asgn._gitlab_path !== undefined? 'Ok' :(asgn.gitlab_project ? 'Change':'Add'),
                button2_title: asgn._gitlab_path !== undefined? 'Cancel' :undefined,
            })}
            ${form_field({
                editable: asgn._gitlab_root_path !== undefined,
                obj: asgn,
                pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                name: '🧑‍🎓 Root Project',
                field: 'gitlab_root',
                value: asgn._gitlab_root_path !== undefined ? asgn._gitlab_root_path : asgn.gitlab_root_project?.name||'',
                link_prefix: asgn._gitlab_root_path !== undefined ? undefined : GITLAB_PREFIX,
                onchange: change_gitlab,
                button_make_onclick: check_gitlab,
                button2_make_onclick: cancel_gitlab,
                button_title: asgn._gitlab_root_path !== undefined? 'Ok' :(asgn.gitlab_root_project ? 'Change':'Add'),
                button2_title: asgn._gitlab_root_path !== undefined? 'Cancel' :undefined,
            })}
            ${form_field({
                editable: asgn._gitlab_test_path !== undefined,
                obj: asgn,
                pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                name: '🧪 Test Project',
                field: 'gitlab_test',
                value: asgn._gitlab_test_path !== undefined ? asgn._gitlab_test_path : asgn.gitlab_test_project?.name||'',
                link_prefix: asgn._gitlab_test_path !== undefined ? undefined : GITLAB_PREFIX,
                onchange: change_gitlab,
                button_make_onclick: check_gitlab,
                button2_make_onclick: cancel_gitlab,
                button_title: asgn._gitlab_test_path !== undefined? 'Ok' :(asgn.gitlab_test_project ? 'Change':'Add'),
                button2_title: asgn._gitlab_test_path !== undefined? 'Cancel' :undefined,

            })}
            <div class="form-field">
                <label for="asgn_release_date">Release date:</label>
                <input
                    type="date"
                    id="asgn_release_date"
                    name="release_date"
                    value=${asgn.release_date?.toISOString().slice(0, 10) || ''}
                />
            </div>
            <div class="form-field">
                <label for="asgn_due_date">Due date:</label>
                <input
                    type="date"
                    id="asgn_due_date"
                    name="due_date"
                    value=${asgn.due_date?.toISOString().slice(0, 10) || ''}
                />
            </div>
            <div class="form-field">
                <label for="asgn_grade_date">Grade-by date:</label>
                <input
                    type="date"
                    id="asgn_grade_date"
                    name="grade_by_date"
                    value=${asgn.grade_by_date?.toISOString().slice(0, 10) || ''}
                />
            </div>
            <div class="form-control">
            <button type="button" onclick=${cancel} ?disabled=${!editable}
                >❌ Cancel Edit</button
            >
            <button type="button" onclick=${editable ? save : edit}
                >${editable ? '💾 Save Assignment' : '🖊️ Edit Assignment'}</button
            >
            </div><div class="log">
            ${asgn._log.map(
                (entry) => html`<li class=${entry[0]}>${entry[1]}</li>`,
            ) || ''}</div
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
export function add_assignment_form(proj_ref = undefined) {
    const asgn = new Assignment({
        id: 0,
        course_id: Course.current?.external_id,
        project_ref: proj_ref,
    });
    asgn.course = Course.current;
    console.log(asgn)
    asgn.release_date = new Date();
    const panel = assignment_panel();
    const get_gitlab_asgn = busy_event_handler(
        async (ev) => {
            asgn._project_ref = (document.getElementById('asgn_project') as HTMLInputElement).value;
            asgn._error = undefined;
            await fill_asgn_form_from_gitlab(asgn);
            if (asgn._error || !asgn.course || !asgn.gitlab_id) {
                show_form();
            } else {
                edit_assignment_form(asgn, true, panel);
            }
        },
        () => {},
    );
    const show_form = () => {
        console.log('show_form', asgn);
        render(
            panel,
            html`
                <form>
                    ${!asgn.course.external_id ? html`<div class="error">No course selected!</div>` : ''}
                    <label for="asgn_project">Gitlab project:</label>
                    <input
                        type="text"
                        id="asgn_project"
                        name="project_ref"
                        placeholder="URL or path or project id"
                        value=${asgn._project_ref || ''}
                    />
                    <div class="buttons">
                        <button type="button" id="asgn_project_from" onclick=${get_gitlab_asgn}
                            >New assignment</button
                        >
                    </div>
                    ${asgn._error ? html`<div class="error">${asgn._error}</div>` : ''}
                </form>
            `,
        );
    };
    show_form();
}
async function fill_asgn_form_from_gitlab(asgn: Assignment) {
    if (asgn._project_ref) {
        const proj = await get_gitlab_project(asgn.course.external_id, asgn._project_ref);
        if (proj?.id) {
            asgn.gitlab_id = proj.id;
            asgn.description = proj.description;
            asgn.name = proj.name;
            asgn.slug = proj.path;
        } else {
            asgn._error = proj.message;
        }
        return asgn;
    }
    throw new Error('Function not implemented.');
}
