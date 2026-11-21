import { expect, test } from "./fixtures";

test("YouTube opens the channel library and preserves reading selections", async ({page}) => {
  await page.goto("/");
  await page.getByTestId("nav-youtube").click();
  const feed = page.frameLocator('iframe[title*="YouTube"]');
  const list = feed.locator("#documents li");
  await expect(list.first()).toBeVisible();
  const frame = page.locator('iframe[title*="YouTube"]');
  for (const width of [1440, 1100]) {
    await page.setViewportSize({ width, height: 850 });
    await expect.poll(() => frame.evaluate(node => {
      const pane = node.getBoundingClientRect();
      const shell = node.parentElement!.getBoundingClientRect();
      return Math.max(Math.abs(shell.right - pane.right), Math.abs(shell.bottom - pane.bottom));
    })).toBeLessThanOrEqual(1);
    await expect(list.first()).toBeInViewport();
  }
  const title = await list.first().locator(".title").textContent();
  await list.first().getByRole("button", {name:"精选"}).click();
  await feed.getByRole("navigation").getByText("精选").click();
  await expect(list).toHaveCount(1);
  await expect(list.first().locator(".title")).toHaveText(title!);
  await expect(list.first().getByRole("link", {name:"公开链接"})).toHaveAttribute("href", /^https:\/\/vincentshuo.github.io\/Edison\/youtube\/Channel\//);
  const popup = page.waitForEvent("popup");
  await list.first().locator(".title").click();
  expect((await (await popup).waitForLoadState("domcontentloaded"))).toBeUndefined();
  await page.goto("/?module=youtube");
  await feed.getByRole("navigation").getByText("精选").click();
  await expect(list.first().locator(".title")).toHaveText(title!);
});

test("global sidebar browses channels before navigating", async ({page}) => {
  await page.goto("/");
  await page.getByTestId("nav-curriculum").click();
  const sidebar = page.locator(".sidebar");
  await sidebar.dispatchEvent("wheel", {deltaX: 80, deltaY: 1});
  const channel = sidebar.getByRole("button", {name: /^AI Engineer/});
  await expect(channel).toBeVisible();
  await expect(page.locator('iframe[title*="YouTube"]')).toHaveCount(0);
  await channel.click();
  const feed = page.frameLocator('iframe[title*="YouTube"]');
  await expect(feed.locator("#channel-name")).toHaveText("AI Engineer");
  await expect(feed.locator("aside")).toBeHidden();
  await expect(feed.locator("#documents li").first()).toBeVisible();
  await sidebar.getByRole("button", {name: /^a16z/}).click();
  await expect(feed.locator("#channel-name")).toHaveText("a16z");
  // Reverse in the same event burst, including same-direction inertia.
  await sidebar.evaluate(node => {
    for (const deltaX of [80, 8, 3, -20, -25]) {
      node.dispatchEvent(new WheelEvent("wheel", {deltaX, cancelable:true}));
    }
  });
  await expect(page.getByTestId("nav-youtube")).toBeVisible();
  await sidebar.dispatchEvent("wheel", {deltaX: 80});
  const scroll = sidebar.locator(".channel-directory-list");
  await expect(scroll).toHaveCSS("scrollbar-width", "none");
  await expect.poll(() => scroll.evaluate(node => {
    node.scrollTop = 100;
    return node.scrollTop;
  })).toBeGreaterThan(0);
  await sidebar.dispatchEvent("wheel", {deltaX: -80});
  await expect(page.getByTestId("nav-youtube")).toBeVisible();
  await expect(feed.locator("#channel-name")).toHaveText("a16z");
});
