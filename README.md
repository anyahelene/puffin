# Puffin v2.0


## Developer setup

### Starting

```
flask --debug -A puffin.app.app run
```

Connect to http://localhost:5000/ 

GitLab login at http://localhost:5000/login/gitlab

### Console commands

#### Set active course

```javascript
await puffin.Course.setActiveCourse(39903); puffin.CourseView.set_course_view()
```

#### Refresh course list

```javascript
await puffin.Course.updateCourses()
```

#### Show course page with sync button (move this!)

```javascript
await puffin.CourseView.display_course(puffin.Course.current)
```

#### New assignmentsd5
```javascript
puffin.edit_assignment_form()
```


```javascript
urls = ["https://git.app.uib.no/blasters/bomb-person",
"https://git.app.uib.no/ojafe/tower-defence",
"https://git.app.uib.no/microissant/project-gluten",
"https://git.app.uib.no/ostehovellen/cdg",
"https://git.app.uib.no/knights-of-the-round-screen/ChessTD",
"https://git.app.uib.no/code-koala-team/project-koala",
"https://git.app.uib.no/fury-panda/fury-panda-v23",
"https://git.app.uib.no/mavenless/rona-survivors",
"https://git.app.uib.no/proghub/catfight",
"https://git.app.uib.no/super-boys/inf112-v23-project",
"https://git.app.uib.no/cosmic-crusade-studios/battle-against-the-cosmic-crusaders",
"https://git.app.uib.no/rattlinboge/bogesquest",
"https://git.app.uib.no/sorkanten/top-down-squad",
"https://git.app.uib.no/javajunkies/shmup ",
"https://git.app.uib.no/bomb-squad/bomb-squad",
"https://git.app.uib.no/SagaOfTheVilleins/sagaofthevilleins",
"https://git.app.uib.no/malicious-malware/kaijumon",
"https://git.app.uib.no/hackermens1/terminaljumper",
"https://git.app.uib.no/team-team/team-team-2023-platformer-project",
"https://git.app.uib.no/java-junkies/inf112.23v.javafx-template",
"https://git.app.uib.no/bit-by-bit/sir-slay-a-lot",
"https://git.app.uib.no/karmoywarios/hyttetur",
"https://git.app.uib.no/gruppe404/alien-invaders",
"https://git.app.uib.no/hero-weirusi/inf112-23v-hero_weirusi",
"https://git.app.uib.no/akuttens-stamkunder/joakims-pinatas",
"https://git.app.uib.no/gossip-girls/terrario",
"https://git.app.uib.no/inf112-gruppe5team2/mousemilitants",
]

for(const u of urls) await puffin.create_team_from_project_url(puffin.Course.current, u)

all_teams=[]; puffin.Course.current.groups.filter(g => g.kind === 'team').forEach(g => {all_teams.push(`${g.slug},${g.join_source.slice(g.join_source.indexOf('(')+1,g.join_source.indexOf(')'))}\n`)}); all_teams.sort((a,b) => a.localeCompare(b)); console.log(all_teams.join(''))

all_students=[]; puffin.Course.current.groups.filter(g => g.kind === 'team').forEach(g => {g.members.forEach(u => {all_students.push(`${u.slug},${u.lastname},${u.firstname},${g.slug}\n`)})}); all_students.sort((a,b) => a.localeCompare(b));console.log(all_students)