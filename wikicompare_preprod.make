; ----------------
; Generated makefile from http://drushmake.me
; Permanent URL: http://drushmake.me/file.php?token=b87bca000221
; ----------------
;
; This is a working makefile - try it! Any line starting with a `;` is a comment.
  
; Core version
; ------------
; Each makefile should begin by declaring the core version of Drupal that all
; projects should be compatible with.
  
core = 7.x
  
; API version
; ------------
; Every makefile needs to declare its Drush Make API version. This version of
; drush make uses API version `2`.
  
api = 2
  
; Core project
; ------------
; In order for your makefile to generate a full Drupal site, you must include
; a core project. This is usually Drupal core, but you can also specify
; alternative core projects like Pressflow. Note that makefiles included with
; install profiles *should not* include a core project.
  
; Drupal 7.x. Requires the `core` property to be set to 7.x.
projects[drupal][version] = 7

  
  
; Modules
; --------
projects[] = admin_menu
projects[] = bakery
projects[] = ctools
projects[] = devel
projects[] = diff
projects[] = imce
projects[] = entity
projects[] = entityreference
projects[] = ckeditor
projects[] = lang_dropdown
projects[] = privatemsg
projects[] = views
projects[] = revisioning
projects[] = simple_dialog
projects[] = piwik
projects[] = userone
projects[wikicompare][type] = "module"
projects[wikicompare][download][type] = "git"
projects[wikicompare][download][url] = "https://github.com/YannickB/wikicompare.git"
projects[wikicompare][download][branch] = "dev"
libraries[ckeditor][download][type] = "get"
libraries[ckeditor][download][url] = "http://download.cksource.com/CKEditor/CKEditor/CKEditor%203.6.3/ckeditor_3.6.3.tar.gz"
  

; Themes
; --------
projects[] = zen
projects[wikicompare_theme][type] = "theme"
projects[wikicompare_theme][download][type] = "git"
projects[wikicompare_theme][download][url] = "https://github.com/YannickB/wikicompare_theme.git"
  
  
; Libraries
; ---------
; No libraries were included


