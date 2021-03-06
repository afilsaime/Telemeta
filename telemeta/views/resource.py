# -*- coding: utf-8 -*-
# Copyright (C) 2007-2010 Samalyse SARL
# Copyright (C) 2010-2012 Parisson SARL

# This software is a computer program whose purpose is to backup, analyse,
# transcode and stream any audio content with its metadata over a web frontend.

# This software is governed by the CeCILL  license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".

# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.

# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.

# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.

# Authors: Olivier Guilyardi <olivier@samalyse.com>
#          Guillaume Pellerin <yomguy@parisson.com>


from telemeta.views.core import *


class ResourceView(object):
    """Provide Resource web UI methods"""

    types = {'corpus':
                {'model': MediaCorpus,
                'form' : MediaCorpusForm,
                'related': MediaCorpusRelated,
                'parent': MediaFonds,
                },
            'fonds':
                {'model': MediaFonds,
                'form' : MediaFondsForm,
                'related': MediaFondsRelated,
                'parent': None,
                }
            }

    def setup(self, type):
        self.model = self.types[type]['model']
        self.form = self.types[type]['form']
        self.related = self.types[type]['related']
        self.parent = self.types[type]['parent']
        self.type = type

    def detail(self, request, type, public_id, template='telemeta/resource_detail.html'):
        self.setup(type)
        resource = self.model.objects.get(code=public_id)
        children = resource.children.all()
        children = children.order_by('code')
        related_media = self.related.objects.filter(resource=resource)
        check_related_media(related_media)
        playlists = get_playlists(request)
        revisions = Revision.objects.filter(element_type=type, element_id=resource.id).order_by('-time')
        if revisions:
            last_revision = revisions[0]
        else:
            last_revision = None
        if self.parent:
            parents = self.parent.objects.filter(children=resource)
        else:
            parents = []

        return render(request, template, {'resource': resource, 'type': type, 'children': children,
                        'related_media': related_media, 'parents': parents, 'playlists': playlists,
                        'last_revision': last_revision })

    def edit(self, request, type, public_id, template='telemeta/resource_edit.html'):
        self.setup(type)
        resource = self.model.objects.get(code=public_id)
        if request.method == 'POST':
            form = self.form(data=request.POST, files=request.FILES, instance=resource)
            if form.is_valid():
                code = form.cleaned_data['code']
                if not code:
                    code = public_id
                form.save()
                resource.set_revision(request.user)
                return redirect('telemeta-resource-detail', self.type, code)
        else:
            form = self.form(instance=resource)
        return render(request, template, {'resource': resource, 'type': type, 'form': form,})

    def add(self, request, type, template='telemeta/resource_add.html'):
        self.setup(type)
        resource = self.model()
        if request.method == 'POST':
            form = self.form(data=request.POST, files=request.FILES, instance=resource)
            if form.is_valid():
                code = form.cleaned_data['code']
                if not code:
                    code = public_id
                form.save()
                resource.set_revision(request.user)
                return redirect('telemeta-resource-detail', self.type, code)
        else:
            form = self.form(instance=resource)
        return render(request, template, {'resource': resource, 'type': type, 'form': form,})

    def copy(self, request, type, public_id, template='telemeta/resource_edit.html'):
        self.setup(type)
        if request.method == 'POST':
            resource = self.model()
            form = self.form(data=request.POST, files=request.FILES, instance=resource)
            if form.is_valid():
                code = form.cleaned_data['code']
                if not code:
                    code = public_id
                resource.save()
                resource.set_revision(request.user)
                return redirect('telemeta-resource-detail', self.type, code)
        else:
            resource = self.model.objects.get(code=public_id)
            form = self.form(instance=resource)
        return render(request, template, {'resource': resource, 'type': type, "form": form,})

    def playlist(self, request, type, public_id, template, mimetype):
        self.setup(type)
        try:
            resource = self.model.objects.get(code=public_id)
        except ObjectDoesNotExist:
            raise Http404

        template = loader.get_template(template)
        context = RequestContext(request, {'resource': resource, 'host': request.META['HTTP_HOST']})
        return HttpResponse(template.render(context), content_type=mimetype)

    def delete(self, request, type, public_id):
        self.setup(type)
        resource = self.model.objects.get(code=public_id)
        revisions = Revision.objects.filter(element_type='resource', element_id=resource.id)
        for revision in revisions:
            revision.delete()
        resource.delete()
        return HttpResponseRedirect('/archives/'+self.type+'/')

    def related_stream(self, request, type, public_id, media_id):
        self.setup(type)
        resource = self.model.objects.get(code=public_id)
        media = self.related.objects.get(resource=resource, id=media_id)
        response = StreamingHttpResponse(stream_from_file(media.file.path), content_type=media.mime_type)
        return response

    def related_download(self, request, type, public_id, media_id):
        self.setup(type)
        resource = self.model.objects.get(code=public_id)
        media = self.related.objects.get(resource=resource, id=media_id)
        filename = media.file.path.split(os.sep)[-1]
        response = StreamingHttpResponse(stream_from_file(media.file.path), content_type=media.mime_type)
        response['Content-Disposition'] = 'attachment; ' + 'filename=' + filename
        return response


class ResourceMixin(View):

    types = {'corpus':
                {'model': MediaCorpus,
                'form' : MediaCorpusForm,
                'related': MediaCorpusRelated,
                'parent': MediaFonds,
                'inlines': [CorpusRelatedInline,]
                },
            'fonds':
                {'model': MediaFonds,
                'form' : MediaFondsForm,
                'related': MediaFondsRelated,
                'parent': None,
                'inlines': [FondsRelatedInline,]
                }
            }

    def setup(self, type):
        self.model = self.types[type]['model']
        self.form = self.types[type]['form']
        self.form_class = self.types[type]['form']
        self.related = self.types[type]['related']
        self.parent = self.types[type]['parent']
        self.inlines = self.types[type]['inlines']
        self.type = type

    def get_object(self):
        # super(CorpusDetailView, self).get_object()
        self.type = self.kwargs['type']
        self.setup(self.type)
        obj = self.model.objects.filter(code=self.kwargs['public_id'])
        if not obj:
            try:
                obj = self.model.objects.get(id=self.kwargs['public_id'])
            except:
                pass
        else:
            obj = obj[0]
        self.pk = obj.pk
        return get_object_or_404(self.model, pk=self.pk)

    def get_context_data(self, **kwargs):
        context = super(ResourceMixin, self).get_context_data(**kwargs)
        context['type'] = self.type
        return context


class ResourceSingleMixin(ResourceMixin):

    def get_queryset(self):
        self.type = self.kwargs['type']
        self.setup(self.type)
        return self

    def get_object(self):
        # super(CorpusDetailView, self).get_object()
        self.type = self.kwargs['type']
        self.setup(self.type)
        obj = self.model.objects.filter(code=self.kwargs['public_id'])
        if not obj:
            try:
                obj = self.model.objects.get(id=self.kwargs['public_id'])
            except:
                pass
        else:
            obj = obj[0]
        self.pk = obj.pk
        return get_object_or_404(self.model, pk=self.pk)

    def get_context_data(self, **kwargs):
        context = super(ResourceMixin, self).get_context_data(**kwargs)
        resource = self.get_object()
        related_media = self.related.objects.filter(resource=resource)
        check_related_media(related_media)
        playlists = get_playlists_names(self.request)
        revisions = Revision.objects.filter(element_type=self.type, element_id=self.pk).order_by('-time')
        context['resource'] = resource
        context['type'] = self.type
        context['related_media'] = related_media
        context['revisions'] = revisions
        if revisions:
            context['last_revision'] = revisions[0]
        else:
            context['last_revision'] = None
        if self.parent:
            context['parents'] = self.parent.objects.filter(children=resource)
        else:
            context['parents'] = []
        return context


class ResourceListView(ResourceMixin, ListView):

    template_name = "telemeta/resource_list.html"
    paginate_by = 20

    def get_queryset(self):
        self.type = self.kwargs['type']
        self.setup(self.type)
        return self.model.objects.all().order_by('code')

    def get_context_data(self, **kwargs):
        context = super(ResourceListView, self).get_context_data(**kwargs)
        context['count'] = self.object_list.count()
        return context


class ResourceDetailView(ResourceSingleMixin, DetailView):

    template_name = "telemeta/resource_detail.html"


class ResourceDetailDCView(ResourceDetailView):

    template_name = "telemeta/resource_detail_dc.html"


class ResourceAddView(ResourceMixin, CreateView):

    template_name = 'telemeta/resource_add.html'

    def get_queryset(self):
        self.type = self.kwargs['type']
        self.setup(self.type)
        return self

    def get_success_url(self):
        return reverse_lazy('telemeta-resource-list', kwargs={'type':self.kwargs['type']})

    @method_decorator(permission_required('telemeta.add_mediacorpus'))
    @method_decorator(permission_required('telemeta.add_mediafonds'))
    def dispatch(self, *args, **kwargs):
        return super(ResourceAddView, self).dispatch(*args, **kwargs)


class ResourceCopyView(ResourceSingleMixin, ResourceAddView):

    template_name = 'telemeta/resource_edit.html'

    def get_initial(self):
        return model_to_dict(self.get_object())

    def get_success_url(self):
        return reverse_lazy('telemeta-resource-list', kwargs={'type':self.kwargs['type']})
        # return reverse_lazy('telemeta-resource-detail', kwargs={'type':self.kwargs['type'], 'public_id':self.kwargs['public_id']})

    @method_decorator(permission_required('telemeta.add_mediacorpus'))
    @method_decorator(permission_required('telemeta.add_mediafonds'))
    def dispatch(self, *args, **kwargs):
        return super(ResourceCopyView, self).dispatch(*args, **kwargs)


class ResourceDeleteView(ResourceSingleMixin, DeleteView):

    template_name = 'telemeta/resource_confirm_delete.html'

    def get_success_url(self):
         return reverse_lazy('telemeta-resource-list', kwargs={'type':self.kwargs['type']})

    @method_decorator(permission_required('telemeta.delete_mediacorpus'))
    @method_decorator(permission_required('telemeta.delete_mediafonds'))
    def dispatch(self, *args, **kwargs):
        return super(ResourceDeleteView, self).dispatch(*args, **kwargs)


class ResourceEditView(ResourceSingleMixin, UpdateWithInlinesView):

    template_name = 'telemeta/resource_edit.html'

    def get_success_url(self):
        return reverse_lazy('telemeta-resource-detail', kwargs={'type':self.kwargs['type'], 'public_id':self.kwargs['public_id']})

    @method_decorator(permission_required('telemeta.change_mediacorpus'))
    @method_decorator(permission_required('telemeta.change_mediafonds'))
    def dispatch(self, *args, **kwargs):
        return super(ResourceEditView, self).dispatch(*args, **kwargs)


def cleanup_path(path):
    new_path = []
    for dir in path.split(os.sep):
        new_path.append(slugify(dir))
    return os.sep.join(new_path)


class CorpusEpubView(View):

    model = MediaCorpus

    def get_object(self):
        return MediaCorpus.objects.get(public_id=self.kwargs['public_id'])

    def get(self, request, *args, **kwargs):
        """
        Stream an Epub file of collection data
        """
        from collections import OrderedDict
        from ebooklib import epub
        from django.template.loader import render_to_string

        book = epub.EpubBook()
        corpus = self.get_object()
        local_path = os.path.dirname(__file__)
        css = os.sep.join([local_path, '..', 'static', 'telemeta', 'css', 'telemeta_epub.css'])
        collection_template = os.sep.join([local_path, '..', 'templates', 'telemeta', 'collection_epub.html'])
        site = Site.objects.get_current()

        # add metadata
        book.set_identifier(corpus.public_id)
        book.set_title(corpus.title)
        book.set_language('fr')
        book.add_author(corpus.descriptions)

        # add cover image
        for media in corpus.related.all():
            if 'cover' in media.title or 'Cover' in media.title:
                book.set_cover("cover.jpg", open(media.file.path, 'r').read())
                break

        chapters = []
        for collection in corpus.children.all():
            items = {}
            for item in collection.items.all():
                if '.' in item.old_code:
                    id = item.old_code.split('.')[1]
                else:
                    id = item.old_code
                id = id.replace('a', '.1').replace('b', '.2')
                items[item] = float(id)
            items = OrderedDict(sorted(items.items(), key=lambda t: t[1]))

            for item in items:
                if item.file:
                    audio = open(item.file.path, 'r')
                    filename = str(item.file)
                    epub_item = epub.EpubItem(file_name=str(item.file), content=audio.read())
                    book.add_item(epub_item)
                for related in item.related.all():
                    if 'image' in related.mime_type:
                        image = open(related.file.path, 'r')
                        epub_item = epub.EpubItem(file_name=str(related.file), content=image.read())
                        book.add_item(epub_item)
            context = {'collection': collection, 'site': site, 'items': items}
            c = epub.EpubHtml(title=collection.title, file_name=collection.code + '.xhtml', lang='fr')
            c.content = render_to_string(collection_template, context)
            chapters.append(c)
            # add chapters to the book
            book.add_item(c)

        # create table of contents
        # - add manual link
        # - add section
        # - add auto created links to chaptersfesse

        book.toc = (( chapters ))

        # add navigation files
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # add css style
        style = open(css, 'r')
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style.read())
        book.add_item(nav_css)

        # create spin, add cover page as first page
        chapters.insert(0,'nav')
        chapters.insert(0,'cover')
        book.spine = chapters

        # create epub file
        filename = '/tmp/test.epub'
        epub.write_epub(filename, book, {})
        epub_file = open(filename, 'rb')

        response = HttpResponse(epub_file.read(), content_type='application/epub+zip')
        response['Content-Disposition'] = "attachment; filename=%s.%s" % \
                                             (collection.code, 'epub')
        return response

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(CorpusEpubView, self).dispatch(*args, **kwargs)
