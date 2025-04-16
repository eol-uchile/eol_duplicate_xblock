# EOL Duplicate Xblock

![Coverage Status](/coverage-badge.svg)

![https://github.com/eol-uchile/eol_duplicate_xblock/actions](https://github.com/eol-uchile/eol_duplicate_xblock/workflows/Python%20application/badge.svg)

Duplicate a block_id in any user course

# Install App
```
docker-compose exec cms pip install -e /openedx/requirements/eol_duplicate_xblock
```
# Configuration

Edit *production.py* in *cms and lms settings*.

    CORS_ALLOW_CREDENTIALS = True
    CORS_ORIGIN_WHITELIST = ['studio.domain.com']
    CORS_ALLOW_HEADERS = corsheaders_default_headers + (
        'use-jwt-cookie',
    )

# Install Theme

To enable duplicate-xblock button in your theme add next files and/or lines code:

- _../themes/your_theme/cms/templates/container.html_ and  _../themes/your_theme/cms/templates/course_outline.html_

    **Add in <%block name="header_extras">**
    ```
    <script type="text/javascript" src="${static.url('eol_duplicate_xblock/js/eol_copy_xblock.js')}"></script>
    <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function(){ 
            $("#eol_duplicate_xblock_div").load("${static.url('eol_duplicate_xblock/html/copy-to-other-course.html')}");
        }, false);
    </script>
    ```

    **and in <%block name="content">**
    ```
    <div id="eol_duplicate_xblock_div"></div>
    ```

- _../themes/your_theme/cms/templates/studio_xblock_wrapper.html_
    ```
    <li class="action-item action-duplicate">
        <a href="#" onclick="duplicar_xblock('${xblock.location}', '${label | n, js_escaped_string}');" data-tooltip="Duplicar a otro Curso" class="copy-to-other-course-button action-button">
            <span class="icon fa fa-share-square-o" aria-hidden="true"></span>
            <span class="sr action-button-text">Duplicar a otro Curso</span>
        </a>
    </li>
    ```
- _../themes/your_theme/cms/templates/js/course-outline.underscore_
    ```
    <%
        var display_name_duplicar = xblockInfo.get('display_name').replace(/'/g,"")
        display_name_duplicar = display_name_duplicar.replace(/"/g,"")
    %>
        <li class="action-item action-copy-to-other-course">
        <a href="#" onclick="duplicar_xblock('<%- xblockInfo.get('id') %>', '<%- display_name_duplicar %>');" data-tooltip="Duplicar a otro Curso" class="copy-to-other-course-button action-button">
            <span class="icon fa fa-share-square-o" aria-hidden="true"></span>
            <span class="sr action-button-text">Duplicar a otro Curso</span>
        </a>
    </li>
    ```
        
## TESTS
**Prepare tests:**

- Install **act** following the instructions in [https://nektosact.com/installation/index.html](https://nektosact.com/installation/index.html)

**Run tests:**
- In a terminal at the root of the project
    ```
    act -W .github/workflows/pythonapp.yml
    ```
