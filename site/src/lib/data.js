const payloadCache = new Map();

async function fetchJson(name) {
  const response = await fetch(`${import.meta.env.BASE_URL}data/${name}.json`);
  if (!response.ok) {
    throw new Error(`加载 ${name} 失败：${response.status}`);
  }
  return response.json();
}

function loadCached(name, parser) {
  if (!payloadCache.has(name)) {
    const task = fetchJson(name)
      .then((payload) => parser(payload))
      .catch((error) => {
        payloadCache.delete(name);
        throw error;
      });
    payloadCache.set(name, task);
  }
  return payloadCache.get(name);
}

function decodeRows(payload) {
  return payload.items.map((row) =>
    Object.fromEntries(payload.fields.map((field, index) => [field, row[index]])),
  );
}

export function loadOverview() {
  return loadCached('overview_kpis', (payload) => payload);
}

export function loadMods() {
  return loadCached('mods', (payload) => ({
    meta: payload.meta,
    items: decodeRows(payload).map((record) => ({
      id: record.id,
      title: record.t,
      searchKey: record.k,
      creatorId: record.cid,
      subscriptions: record.s,
      votesUp: record.up,
      votesDown: record.down,
      score: record.sc,
      positiveRate: record.pr,
      createdAt: record.ct,
      updatedAt: record.ut,
      maintenanceDays: record.md,
      daysSinceLastUpdate: record.du,
      subscriptionMedian: record.sm,
      maintenanceMedian: record.mm,
      quadrant: record.q,
      quadrantLabel: record.ql,
      tags: record.tg ?? [],
      rank: record.rk,
    })),
  }));
}

export function loadAuthors() {
  return loadCached('authors', (payload) => ({
    meta: payload.meta,
    items: decodeRows(payload).map((record) => ({
      id: record.id,
      modCount: record.mc,
      totalSubscriptions: record.ts,
      avgSubscriptions: record.as,
      medianSubscriptions: record.ms,
      avgPositiveRate: record.pr,
      avgMaintenanceDays: record.amd,
      tagBreadth: record.tb,
      rank: record.rk,
      productivityBucket: record.pb,
      sharePct: record.sp,
      cumulativeSharePct: record.cp,
      concentrationBand: record.cb,
      mods: record.mods ?? [],
    })),
  }));
}

export function loadSupplyDemandTags() {
  return loadCached('tags_supply_demand', (payload) => ({
    meta: payload.meta,
    items: decodeRows(payload).map((record) => ({
      tag: record.tag,
      modCount: record.mc,
      avgSubscriptions: record.avg,
      medianSubscriptions: record.med,
      p75Subscriptions: record.p75,
      isStableTag: record.stable === 1,
      supplyThreshold: record.st,
      demandThreshold: record.dt,
      p75Threshold: record.pt,
      supplySide: record.ss,
      demandSide: record.ds,
      marketZone: record.zone,
    })),
  }));
}

export function loadDimTags() {
  return loadCached('dim_tags', (payload) => ({
    meta: payload.meta,
    items: decodeRows(payload).map((record) => ({
      tag: record.tag,
      modCount: record.mc,
      avgSubscriptions: record.avg,
      rank: record.rk,
      weight: record.w,
    })),
  }));
}

export function loadCommentKeywords() {
  return loadCached('comments_keywords', (payload) => ({
    meta: payload.meta,
    groups: payload.meta.groups,
    items: decodeRows(payload).map((record) => ({
      token: record.t,
      dominantGroup: record.g,
      top100CommentCount: record.c1,
      rank300500CommentCount: record.c2,
      top100Per1000: record.p1,
      rank300500Per1000: record.p2,
      diffPer1000: record.d,
      rateRatio: record.rr,
    })),
  }));
}
