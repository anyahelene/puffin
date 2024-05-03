import { Hole, html, render } from 'uhtml';
import { busy_event_handler, get_gitlab_project, request, to_table } from './puffin';
import { BorbPanel, BorbPanelBuilder } from '../borb/Frames';
import { Course, Group } from './model';
import { pick_project_form, project_field } from './gitlab';
import { SLUG_RE, form_field } from './forms';
import slugify from 'slugify';

function team_panel() {
    return new BorbPanelBuilder()
        .frame('frame2')
        .panel('form', 'edit-team')
        .title('New team')
        .select()
        .done();
}
export function add_many_teams_form() {
    const form_data: Record<string, any> = {};
    form_data.course_id = Course.current?.external_id;
    const panel = team_panel();
    return new Promise((resolve, reject) => {
        const textarea_ref: { current?: HTMLTextAreaElement } = {};
        const team_table_data: Record<string, any>[] = [];
        const created_teams: Record<string, any>[] = [];
        const cancel = () => {
            render(panel, html``);
            panel.remove();
            reject('Cancelled');
        };
        const decode = () => {
            const textarea = textarea_ref.current;
            const lines = textarea.value.split('\n');
            const bad_lines = [];
            lines.forEach((line, i) => {
                try {
                    const [team_name, groupno, project_path] = line
                        .split('\t')
                        .map((s) => s.trim());
                    const group = Course.current.groupsBySlug.get(`gruppe-${groupno}`);
                    if (team_name !== '' || project_path !== '') {
                        const data = {
                            course: form_data.course_id,
                            name: team_name,
                            _project_path: project_path,
                            parent_id: group.id,
                            slug: slugify(team_name, { lower: true, strict: true }),
                        };
                        console.log('decoded: ', data);
                        team_table_data.push(data);
                    }
                } catch (e) {
                    console.error('While decoding team list', e);
                    bad_lines.push(line);
                }
            });
            textarea.value = bad_lines.join('\n');
            console.log('decode', textarea_ref);
            redraw();
        };
        const save = async () => {
            const teams = team_table_data.splice(0);
            teams.forEach((team) => {
                if (team.name && team.slug && team.project_project) {
                    request(
                        `courses/${form_data.course_id}${
                            team.parent_id ? `/groups/${team.parent_id}` : ''
                        }/teams/`,
                        'POST',
                        {
                            name: team.name,
                            slug: team.slug,
                            project_path: team.project_project.path_with_namespace,
                            parent_id: team.parent_id || null,
                            project_id: team.project_project.id,
                            project_name: team.project_project.name,
                        },
                    )
                        .then((result) => {
                            console.log('Created team: ', result);
                            result.sync_ok = 'pending';
                            created_teams.push(result);
                            redraw();
                            request(
                                `courses/${form_data.course_id}/groups/${result.id}/sync`,
                                'POST',
                            )
                                .then((r2) => {
                                    console.log('synced group', r2);
                                    result.sync_ok = 'synced';
                                    redraw();
                                })
                                .catch((err) => {
                                    console.error(err);
                                    result.sync_ok = 'failed';
                                    redraw();
                                });
                        })
                        .catch((err) => {
                            if (err.data.not_unique) {
                                team._error = `Team already exists: ${err.data.not_unique}`;
                            }
                            console.warn(team, err.data);
                            console.error(err);
                            team_table_data.push(team);
                            redraw();
                        });
                } else {
                    team_table_data.push(team);
                    redraw();
                }
            });
            redraw();
        };
        let __redraw_todo = false;

        const redraw = (really = false) => {
            if (!really) {
                if (!__redraw_todo) {
                    queueMicrotask(() => redraw(true));
                    __redraw_todo = true;
                }
                return;
            }
            __redraw_todo = false;
            console.log('redraw  all teams form', team_table_data);
            const form = html`
                <textarea
                    cols="80"
                    rows="5"
                    autocomplete="off"
                    autocorrect="off"
                    ref=${textarea_ref}
                    .hidden=${team_table_data.length > 0 && textarea_ref.current.value === ''}
                    placeholder="team_name<TAB>group_no<TAB>project_url"
                ></textarea>
                <div class="form-control">
                    <button type="button" onclick=${decode}>Read teams from text area</button>
                </div>
                <table>
                    <thead>
                        <tr
                            ><th>Team name</th><th>Slug</th><th>Parent group</th
                            ><th>Team project</th></tr
                        >
                    </thead>
                    <tbody>
                        ${team_table_data.map((data) => team_table_form(data, redraw))}
                    </tbody></table
                >
                <div class="form-control">
                    <button type="button" onclick=${cancel}>❌ Cancel</button>
                    <button type="button" onclick=${save}>Save teams</button>
                </div>
                <div><borb-sheet>${to_table(created_teams)}</borb-sheet></div>
                <div class="log">
                    ${form_data._log?.map(
                        (entry) => html`<li class=${entry[0]}>${entry[1]}</li>`,
                    ) || ''}</div
                >
            `;
            render(panel, form);
        };
        redraw();
    });
}
export function team_table_form(form_data: Record<string, any>, redraw): Hole {
    const has_valid_project = (p) => {
        console.log('has_valid_project');
        if (!form_data.name) {
            form_data.name = p.name;
        }
    };

    const form = html`<tr>
        <td>
            ${form_data._error ? html`<div class="error">${form_data._error}</div>` : ''}
            ${form_field({
                editable: true,
                obj: form_data,
                name: 'Team Name',
                field: 'name',
                required: true,
                label: false,
                value: form_data.name,
            })}
        </td>
        <td>
            ${form_field({
                editable: true,
                obj: form_data,
                name: 'Team Slug',
                pattern: SLUG_RE,
                field: 'slug',
                required: true,
                label: false,
                value: form_data.slug,
            })}
        </td>
        <td>
            ${form_field({
                editable: true,
                obj: form_data,
                name: 'Parent',
                field: 'parent_id',
                required: false,
                label: false,
                size: 5,
                value: form_data.parent_id,
            })}
        </td>
        <td>
            ${project_field(
                {
                    obj: form_data,
                    name: 'Team Project',
                    field: 'project',
                    required: true,
                    label: false,
                    on_valid_project: has_valid_project,
                    value: '',
                },
                redraw,
            )}</td
        ></tr
    >`;
    return form;
}
export async function add_team_form(proj_ref = undefined) {
    const form_data: Record<string, any> = {};
    form_data.course_id = Course.current?.external_id;
    console.log('add_team_form:', form_data);
    const panel = team_panel();
    let editable = true;
    const cancel = (ev) => {
        editable = false;
        redraw();
    };
    const save = (ev) => {
        editable = false;
        redraw();
    };
    const edit = (ev) => {
        editable = true;
        redraw();
    };
    const has_valid_project = (p) => {
        if (!form_data.name) {
            form_data.name = p.name;
        }
    };
    const is_valid = () => {
        return !!form_data['project_project'];
    };
    const redraw = () => {
        console.log('redraw team form');
        const form = html`
            ${form_field({
                editable,
                obj: form_data,
                name: 'Team Name',
                field: 'name',
                required: true,
            })}
            ${project_field(
                {
                    editable,
                    obj: form_data,
                    name: 'Team Project',
                    field: 'project',
                    required: true,
                    on_valid_project: has_valid_project,
                    value: '',
                },
                redraw,
            )}
            <div class="form-control">
                <button type="button" onclick=${cancel} ?disabled=${!editable}
                    >❌ Cancel Edit</button
                >
                <button
                    type="button"
                    .disabled=${editable && !is_valid()}
                    onclick=${editable ? save : edit}
                    >${editable ? '💾 Save Team' : '🖊️ Edit Team'}</button
                > </div
            ><div class="log">
                ${form_data._log?.map((entry) => html`<li class=${entry[0]}>${entry[1]}</li>`) ||
                ''}</div
            >
        `;
        render(panel, form);
    };

    redraw();
}
