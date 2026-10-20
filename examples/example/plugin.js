// Example plugin for TouchDeck. Everything a plugin may do goes through the object `td`.

// Action "Greet": the returned text shows up as a message in the editor and the log.
td.action('greet', (params) => {
  const greeting = td.settings.greeting || 'Hello';
  return `${greeting}, ${params.name || 'world'}!`;
});

// Action "Count up": reads and writes a TouchDeck value (permission "values").
td.action('count', (params) => {
  const name = params.value || 'Example.Counter';
  const next = (Number(td.values.get(name)) || 0) + 1;
  td.values.set(name, next);
  // Own trigger: events in TouchDeck can react to it.
  if (next % 10 === 0) td.fire('ten', { value: name, Count: next });
  return `${name} = ${next}`;
});

// Action "GitHub stars": internet only to the addresses listed in permissions.http.
td.action('stars', (params) => {
  const res = td.http({ url: `https://api.github.com/repos/${params.repo}`, headers: { 'User-Agent': 'TouchDeck-Plugin' } });
  if (!res.ok) throw new Error(`GitHub answered with ${res.status}`);
  return `${params.repo}: ${res.json().stargazers_count} ⭐`;
});

// Action with data: return an object instead of a text. TouchDeck shows the values (names and units from
// "returns" in plugin.json) and passes them on to the following actions as {Result.stars} etc.
td.action('repo', (params) => {
  const res = td.http({ url: `https://api.github.com/repos/${params.repo}`, headers: { 'User-Agent': 'TouchDeck-Plugin' } });
  if (!res.ok) throw new Error(`GitHub answered with ${res.status}`);
  const r = res.json();
  return { stars: r.stargazers_count, forks: r.forks_count, issues: r.open_issues_count, size: r.size };
});

// Timer: write the current time into a value every 60 seconds.
td.every(60000, () => {
  const now = new Date();
  td.values.set('Example.Time', `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`);
});

td.log('Example plugin ready');
