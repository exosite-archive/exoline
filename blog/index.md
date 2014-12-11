---
layout: default
title: "http://exosite.github.io/exoline/blog"
---
{% assign latest_post = site.posts.first %}
{% capture latest_post_title_with_proper_escaping %}{{ latest_post.title | xml_escape }}{% endcapture %}

<div id="post">
  <h1><a href="{{ latest_post.url }}" title="{{ latest_post_title_with_proper_escaping }}">{{ latest_post_title_with_proper_escaping }}</a></h1>

  {% if latest_post.date != null %}
    <span class="published_on">
      Published on {{ latest_post.date | date: "%A, %B %d, %Y" }}

      {% if latest_post.tags != null %}
        in
        {% for tag in latest_post.tags %}
          {% if forloop.last and forloop.length > 1 %} and {% endif %}
          <a href="#" class="tag">{{tag | downcase}}</a>{% if forloop.last == false and forloop.length > 2 %}, {% endif %}
        {% endfor %}
      {% endif %}
     </span>
   {% endif %}

  {{ latest_post.content }}

  <div class="post-footer">
    <a href="{{ latest_post.url }}" title="{{ latest_post_title_with_proper_escaping | xml_escape }}">permalink</a> |
    <a href="{{ latest_post.url }}/#comments" title="{{ latest_post_title_with_proper_escaping }} -- Comments">comments</a> |
  </div>
</div>

<div id="archive">
  <h1><a name="archive" href="#archive" title="Blog Archive">Archive</a></h1>

  <p>Now that you've whetted your appetite with the <a href="{{ latest_post.url }}" title="{{ latest_post.post_title_label }}{{ latest_post_title_with_proper_escaping }}">most recent post</a>, perhaps you'd care to dig into the archive.</p>

  <ul class="posts">
    {% for post in site.posts %}
      {% if post != latest_post %}
        <!-- random comment to work around Jekyll issue -->
        {% include post-li.html %}
      {% endif %}
    {% endfor %}
  </ul>
</div>

