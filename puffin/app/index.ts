import nearley from 'nearley';
import { Settings } from '../borb/Settings';
import { SubSystem } from '../borb/SubSystem';
import { BorbFrame, BorbPanelBuilder } from '../borb/Frames';
import { BorbButton, BorbCommand } from '../borb/Buttons';
import { Styles } from '../borb/Styles';
Styles.pathPrefix = 'static/';
import grammar from '../qlang/qlang.ne';
import slugify from 'slugify';
import { html, render } from 'uhtml';
import { TilingWM, TilingWindow } from '../borb/TilingWM';
import '../borb/css/buttons.scss';
import '../borb/css/common.scss';
import '../borb/css/editor.scss';
import '../borb/css/frames.scss';
import '../borb/css/markdown.scss';
import '../borb/css/sheet.scss';
import '../borb/css/terminal.scss';
import '../css/fonts.scss';
import '../css/style.scss';
import { add_assignment_form, edit_assignment_form } from './assignments';
import { CourseView } from './courses';
import { pick_project_form } from './gitlab';
import { Course, SelfUser, User, Group as PuffinGroup, tables } from './model';
import {
    add_to_table,
    create_team_from_project_url,
    display_panel,
    get_gitlab_group,
    get_gitlab_project,
    gitlab_url,
    login_panel,
    modify_table,
    puffin,
    request,
    to_table,
} from './puffin';
import { add_many_teams_form, add_team_form } from './teams';
import { activate_flashes, show_flash } from './flashes';
//import defaultConfig from './config.json';

const defaultConfig = {};
slugify.extend({ '+': '-' });
puffin.tables = tables;
puffin.Course = Course;
puffin.CourseView = CourseView;
puffin.SubSystem = SubSystem;
puffin.add_assignment_form = add_assignment_form;
puffin.edit_assignment_form = edit_assignment_form;
puffin.get_gitlab_group = get_gitlab_group;
puffin.get_gitlab_project = get_gitlab_project;
puffin.create_team_from_project_url = create_team_from_project_url;
puffin.login_panel = login_panel;
puffin.pick_project_form = pick_project_form;
puffin.add_team_form = add_team_form;
puffin.add_many_teams_form = add_many_teams_form;
window['puffin'] = puffin;
SubSystem.setup(puffin, {
    proxy: true,
    hotReload: !!import.meta.webpackHot,
    global: true,
});
SubSystem.waitFor(Settings).then((settings) => {
    console.warn('CONFIGS:', settings.configs);
    settings.configs[4] = defaultConfig;
});

const layoutPrefs = {
    /*    frame1: {
        width: 12,
        height: 6,
        iconified: false,
        maximized: false,
    },*/
    frame2: {
        width: 32,
        height: 8,
        iconified: false,
        maximized: false,
    },
    frame3: {
        width: 32,
        height: 8,
        iconified: false,
        maximized: false,
    },
};
const layoutSpec = {
    size: 32,
    dir: 'H',
    items: [
        {
            size: 16,
            dir: 'V',
            max_container: true,
            items: [
                {
                    size: 8,
                    item: 'frame2',
                },
                /*              {
                    size: 9,
                    dir: 'H',
                    items: [
                        {
                            size: 0,
                            item: 'frame1',
                        },
                        {
                            size: 14,
                            item: 'frame2',
                        },
                    ],
                },*/
                {
                    size: 8,
                    item: 'frame3',
                },
            ],
        },
    ],
};
interface TilingWM {
    initialize: (spec: object, prefs: object) => void;
}
puffin.TilingWM = TilingWM;
puffin.TilingWindow = TilingWindow;
puffin.BorbButton = BorbButton;
console.log('Hello!!');
const wm = new TilingWM('mid', 32, 16);
puffin.wm = wm;

puffin.courses = CourseView;
puffin.to_table = to_table;
//SubSystem.waitFor(Frames.Frames).then((frames) => {
puffin.display_panel = display_panel;
//});
puffin.nearley = nearley;
puffin.grammar = grammar;
puffin.parser = new nearley.Parser(nearley.Grammar.fromCompiled(grammar));
puffin.request = request;
puffin.show_flash = show_flash;
let reqId = 0;

async function submit(method: string) {
    const endpoint = (document.getElementById('id') as HTMLInputElement).value;
    const value = (document.getElementById('data') as HTMLInputElement).value;
    const requestBody = value ? JSON.parse(value) : undefined;
    console.log('submit', endpoint, requestBody);
    const result = await request(endpoint, method, requestBody);
    console.log('result', result);
    document.getElementById('resultElt').replaceChildren(...to_table(result));
}
document.getElementById('id')?.addEventListener('keydown', enterPressed);
document.getElementById('get')?.addEventListener('click', (e) => submit('GET'));
document.getElementById('put')?.addEventListener('click', (e) => submit('PUT'));
document.getElementById('post')?.addEventListener('click', (e) => submit('POST'));
document.getElementById('patch')?.addEventListener('click', (e) => submit('PATCH'));

interface Group {
    group_id: number;
    group_slug: string;
}

const DATA = {
    groups: [] as Group[],
};

function enterPressed(ev: KeyboardEvent) {
    if (ev.key === 'Enter') {
        submit('GET');
    }
}

async function initialize() {
    activate_flashes();
    if (document.querySelector('body').dataset.endpoint !== 'app.index_html') return;

    // Window manager layout
    wm.initialize(layoutSpec, layoutPrefs);

    const self: SelfUser = await request('users/self/', 'GET', undefined, false, true);
    puffin.self = self;
    Course.current_user = self;
    const user_info = document.getElementById('user-info');
    self.on_update = () => {
        render(
            user_info,
            html`
                <span class="name" title=${self.course_user?.role || ''}
                    >${self.firstname} ${self.lastname}
                    (${self.course_user?.role || (self.is_admin ? 'admin' : 'user')})</span
                >
                <ul class="account-status">
                    <li
                        data-account="canvas"
                        data-account-short="C"
                        data-account-name="Canvas"
                        ?data-is-active=${!!self.canvas_account}
                    ></li>
                    <li
                        data-account="gitlab"
                        data-account-short="G"
                        data-account-name="GitLab"
                        ?data-is-active=${!!self.gitlab_account}
                    ></li>
                    <li
                        data-account="discord"
                        data-account-short="D"
                        data-account-name="Discord"
                        ?data-is-active=${!!self.discord_account}
                    ></li>
                </ul>
                ${self.is_admin
                    ? html`<span class="is-admin" title="Logged in as administrator"
                          ><span></span
                      ></span>`
                    : ''}
                ${self.id != self.real_id
                    ? html`<a class="button line-through" title="deimpersonate" href="login/sudone"
                          >🥸</a
                      >`
                    : ''}
            `,
        );
    };
    await Course.updateCourses(false);
    try {
        const usp = new URLSearchParams(window.location.search);
        let course: Course | undefined;
        if (usp.has('course')) {
            course = Course.courses[parseInt(usp.get('course'))];
        } else {
            course = Course.courses[parseInt(localStorage.getItem('active-course'))];
        }
        if (!course) course = Course.courses.filter(() => true).pop();
        if (course) {
            await course.setActive();
        } else {
            CourseView.update_course_list();
            show_flash('No courses found!');
        }
    } catch (e) {
        console.error('Failed to set active course', e);
    }
    const is_privileged = Course.current_user.course_user?.is_privileged;
    modify_table('Member', 'join_model', (entry) => {
        entry.hide = true;
    });
    if (self.is_admin || is_privileged) {
        console.warn(
            'Choosing admin view',
            'is_admin=',
            self.is_admin,
            'is_privileged=',
            is_privileged,
            'role=',
            Course.current_user.course_user?.role,
        );

        if (self.is_admin) {
            add_to_table('FullUser', 'impersonate', {
                head: ' ',
                mapping: (field, obj, spec) =>
                    html.node`<a class="button" title="impersonate" href="${`login/sudo/${obj.email}`}">🥸</a>`,
                type: 'custom',
            });
        }
        puffin.debug['console'] = true;
        document
            .querySelectorAll('#frame3 [hidden=true]')
            .forEach((p) => p.removeAttribute('hidden'));
        (document.querySelector('#frame3') as BorbFrame).queueUpdate(true);
        CourseView.set_course_view();
    } else {
        modify_table('Member', 'join_model', (entry) => {
            entry.hide = true;
        });
        const debug = puffin.debug['console']
            ? html`<div
                  ><button type="button" onclick=${() => console.log(this)}>Debug</button></div
              >`
            : '';
        const user_panel = new BorbPanelBuilder()
            .frame('frame2')
            .panel('div', 'user_panel')
            .title(`${self.firstname} ${self.lastname}`)
            .select()
            .done();
        const user = Course.current?.usersById[self.id];
        let group = user?.group[0];
        let team = user?.team[0];
        if (user) {
            const avail_teams = async () => {
                const teams = Course.current.groups.filter(
                    (g) => g.kind === 'team' && g.parent_id === group.id,
                );
                const new_team_name = { current: undefined };
                const join_team = (t: PuffinGroup) => async () => {
                    const join_result = await request(
                        `courses/${Course.current.external_id}/teams/${t.id}/users/`,
                        t == team ? 'DELETE' : 'POST',
                        {},
                        false,
                        true,
                    );
                    if (join_result.status === 'error') {
                        show_flash(join_result, 'error');
                    }
                    console.warn(join_result);
                    await Course.current.updateMemberships();
                    team = user.team[0];
                    await redraw();
                };
                const create_team = async (ev) => {
                    if (new_team_name.current) {
                        let name: string = new_team_name.current.value;
                        name = name.trim().replace(/\s+/g, ' ');
                        new_team_name.current.value = name;
                        if (name) {
                            const result = await request(
                                `courses/${Course.current.external_id}/groups/${group.id}/teams/`,
                                'POST',
                                { name },
                            );
                            console.log(result);
                            if (result.status === 'error') {
                                show_flash(result, 'error');
                            } else {
                                new_team_name.current.value = '';
                            }
                            await Course.current.updateGroups();
                            await Course.current.updateMemberships();
                            team = user.team[0];
                            await redraw();
                        }
                    }
                };
                console.warn(teams);
                return html`<fieldset><legend>${group.name} Teams</legend><h4>Pick one:</h4><ul>${teams.map(
                    (t) =>
                        html`<li
                            >${t.as_link(t.name)}
                            <button
                                type="button"
                                ?disabled=${team && t !== team}
                                onclick=${join_team(t)}
                                >${t == team ? 'Leave' : 'Join'}</button
                            ></li
                        >`,
                )}</ul><h4>or create new team:</h4>
                <label for="new-team-name">Team name:</label> <input type="text" ?disabled=${!!team} ref=${new_team_name} id="new-team-name"></input>
                <button type="button" ?disabled=${!!team} onclick=${create_team}>Create!</button></fieldset>`;
            };
            const request_review = async () => {
                const result = await request(
                    `courses/${Course.current.external_id}/teams/reviews/assign/`,
                    'POST',
                    {},
                    false,
                    true,
                );
                console.warn(result);
                if (result.status === 'error') {
                    show_flash(result, 'error');
                } else {
                    await Course.current.updateMemberships();
                    await Course.current.updateUsers();
                    await redraw();
                }
            };
            const redraw = async () => {
                console.warn('Choosing user view', 'user=', user, 'team=', team);
                const team_menu = await avail_teams();
                const review_enabled = false;
                const team_link = team?.json_data.project_path
                    ? html`<a href="${gitlab_url(team?.json_data.project_path)}" target="_blank">
                          ${team?.json_data.project_name} – [${team?.json_data.project_path}]</a
                      >`
                    : html`<em>none</em>`;
                const review_teams = user.findGroups({ kind: 'team', role: 'reviewer' });
                const review_info =
                    review_teams.length > 0
                        ? html`<p><b>Review assignments:</b> </p
                              ><ul
                                  >${review_teams.map(
                                      (t) =>
                                          html`<li
                                              >${t.as_link()}:
                                              <em>${t.json_data.project_name}</em></li
                                          >`,
                                  )}</ul
                              >`
                        : html`<p
                              ><button type="button" onclick=${request_review}
                                  >Request code review assignment</button
                              ></p
                          >`;
                const teamDiv = document.createElement('div');
                if (team) {
                    team.display(teamDiv);
                }
                render(
                    user_panel,
                    html`<h2>${user.firstname} ${user.lastname}</h2
                        ><div class="two-column">
                            ${review_enabled ? review_info : ''}
                            ${team
                                ? html`<fieldset><legend>Your Team</legend>${teamDiv}</fieldset>`
                                : ''}
                            ${team_menu} </div
                        >${debug}`,
                );
            };
            await redraw();
            CourseView.open_team_list();
        } else {
            console.warn('Dunno what to do...', 'user=', user, 'team=', team);
        }
    }

    const retro = (ev: Event) => {
        document
            .querySelector('body')
            .classList.toggle('retro', (ev.target as HTMLInputElement).checked);
    };
    document
        .querySelector('#page-home')
        .appendChild(
            html.node`<borb-button id="retro" onchange=${retro} ?checked=${document.querySelector('body').classList.contains('retro')} type="switch" data-text="Go 8-bit" />`,
        );
}

SubSystem.waitFor('dom').then(() => queueMicrotask(initialize));

if (import.meta.webpackHot) {
    console.warn('WebpackHot enabled');
    //turtleduck.webpackHot = import.meta.webpackHot;
    import.meta.webpackHot.accept(
        [
            '../borb/css/frames.scss',
            '../borb/css/buttons.scss',
            '../borb/css/common.scss',
            '../borb/css/markdown.scss',
            '../borb/css/terminal.scss',
            '../borb/css/editor.scss',
        ],
        function (outdated) {
            outdated.forEach((dep) => {
                console.log(dep);
                //turtleduck.styles.update(dep.replace('./', '').replace('.scss', '.css'));
            });
        },
        (err, context) => {
            console.error('HMR failed:', err, context);
        },
    );

    //  import.meta.webpackHot.accept('./css/frames.scss?raw', function (...args) {
    //		console.warn("frames", args);
    //	});
}
